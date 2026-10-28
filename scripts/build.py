"""Build a week of posts from a brief.

    python scripts/build.py briefs/2026-W45.json

Reads the brief (raw AI media URLs + copy), downloads the raw media, renders branded
slides / Reels with exact brand fonts, writes finished files to docs/media/<week>/ and
the publishing queue to queue/<week>.json.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
CACHE = ROOT / ".cache"
UA = {"User-Agent": "Mozilla/5.0 (tawaana-autopilot build)"}

FPS = 30
XFADE = 0.4


def log(*a):
    print("[build]", *a, flush=True)


def fetch(url_or_path: str) -> Path:
    """Download a remote file once into .cache/ (or resolve a repo-relative path)."""
    if not url_or_path.startswith("http"):
        p = (ROOT / url_or_path).resolve()
        if not p.exists():
            raise FileNotFoundError(url_or_path)
        return p
    CACHE.mkdir(exist_ok=True)
    ext = Path(url_or_path.split("?")[0]).suffix[:6] or ".bin"
    dst = CACHE / (hashlib.sha1(url_or_path.encode()).hexdigest()[:16] + ext)
    if not dst.exists():
        log("download", url_or_path[:90])
        r = requests.get(url_or_path, headers=UA, timeout=180)
        r.raise_for_status()
        dst.write_bytes(r.content)
    return dst


def get_logo() -> Path | None:
    local = ROOT / "assets" / "logo.png"
    if local.exists():
        return local
    try:
        p = fetch(BRAND["logo_url"])
        shutil.copy(p, local)
        return local
    except Exception as e:  # fallback to text wordmark
        log("logo unavailable, using wordmark:", e)
        return None


def shot(page, html: str, out: Path, w: int, h: int, transparent=False):
    page.set_viewport_size({"width": w, "height": h})
    # load from a file:// page so local fonts and photos are allowed
    src = out.with_suffix(".html")
    src.write_text(html)
    page.goto(src.as_uri(), wait_until="load")
    try:
        page.wait_for_function(
            "document.fonts.status === 'loaded' && [...document.fonts].every(f => f.status !== 'loading')"
            " && [...document.fonts].some(f => f.status === 'loaded')"
            " && ![...document.fonts].some(f => f.status === 'error')",
            timeout=15000)
    except Exception as e:
        st = page.evaluate("[...document.fonts].map(f => f.family + ':' + f.status)")
        raise RuntimeError(f"brand fonts failed to load for {out.name}: {st}") from e
    bad = page.evaluate("[...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src)")
    if bad:
        raise RuntimeError(f"images failed to load: {bad}")
    page.wait_for_timeout(150)
    page.screenshot(path=str(out), omit_background=transparent, clip={"x": 0, "y": 0, "width": w, "height": h})


def to_jpeg(png: Path, jpg: Path):
    Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True, progressive=True)


def run(cmd: list[str]):
    log(" ".join(cmd[:6]), "...")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def probe_duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


# ------------------------------------------------------------------ posts

def build_slides(page, post: dict, outdir: Path, logo: Path | None, tmp: Path) -> list[str]:
    slides = post["slides"]
    files = []
    for i, s in enumerate(slides, start=1):
        photo = fetch(s["src"]) if s.get("src") else None
        html = render.feed_slide(s, photo, logo, i, len(slides) if post["type"] == "carousel" else 1)
        png = tmp / f"{post['id']}-{i}.png"
        shot(page, html, png, render.FEED_W, render.FEED_H)
        name = f"slide-{i:02d}.jpg"
        to_jpeg(png, outdir / name)
        files.append(name)
    return files


def has_audio(p: Path) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return bool(out.stdout.strip())


def build_reel(page, post: dict, outdir: Path, logo: Path | None, tmp: Path) -> tuple[list[str], str]:
    """Scenes (AI clips) + text overlays + end card, crossfaded, with the clips' own sound."""
    W, H = render.REEL_W, render.REEL_H
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]
    segs = []
    for i, sc in enumerate(post["scenes"], start=1):
        src = fetch(sc["src"])
        dur = float(sc.get("duration", 0)) or min(probe_duration(src), 5.0)
        start = float(sc.get("start", 0))
        seg = tmp / f"{post['id']}-seg{i}.mp4"
        has_text = bool(sc.get("text") or sc.get("sub") or sc.get("kicker"))
        audio_in = has_audio(src) and not sc.get("mute")
        inputs = ["-ss", str(start), "-t", str(dur), "-i", str(src)]
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,"
              f"setpts=PTS-STARTPTS,format=yuv420p[v]")
        vout = "[v]"
        if has_text:
            ov = tmp / f"{post['id']}-ov{i}.png"
            shot(page, render.reel_overlay(sc), ov, W, H, transparent=True)
            inputs += ["-loop", "1", "-t", str(dur), "-i", str(ov)]
            fc += (f";[1:v]format=rgba,fade=in:st=0.35:d=0.45:alpha=1[o];"
                   f"[v][o]overlay=0:0:shortest=1,format=yuv420p[vt]")
            vout = "[vt]"
        if audio_in:
            fc += f";[0:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur},asetpts=PTS-STARTPTS[a]"
        else:
            idx = 2 if has_text else 1
            inputs += ["-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo"]
            fc += f";[{idx}:a]anull[a]"
        run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", vout, "-map", "[a]",
             "-t", str(dur), *enc, str(seg)])
        segs.append((seg, dur))

    # end card (still image + soft tail of silence, 2.6s)
    end = post.get("end_card")
    if end:
        ecpng = tmp / f"{post['id']}-end.png"
        last_photo = fetch(post["cover"]["src"]) if post.get("cover", {}).get("src") else None
        shot(page, render.reel_end_card(end, logo, last_photo), ecpng, W, H)
        ecseg = tmp / f"{post['id']}-end.mp4"
        run(["ffmpeg", "-y", "-loop", "1", "-t", "2.6", "-i", str(ecpng), "-f", "lavfi", "-t", "2.6",
             "-i", "anullsrc=r=48000:cl=stereo", "-vf", f"fps={FPS},format=yuv420p,fade=in:st=0:d=0.3",
             "-t", "2.6", *enc, str(ecseg)])
        segs.append((ecseg, 2.6))

    # crossfade video and audio
    inputs, chain, offset = [], "", 0.0
    for s, _ in segs:
        inputs += ["-i", str(s)]
    vl, al = "[0:v]", "[0:a]"
    for i in range(1, len(segs)):
        offset += segs[i - 1][1] - XFADE
        chain += f"{vl}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[v{i}];"
        chain += f"{al}[{i}:a]acrossfade=d={XFADE}[a{i}];"
        vl, al = f"[v{i}]", f"[a{i}]"
    total = sum(d for _, d in segs) - XFADE * (len(segs) - 1)
    mixed = tmp / f"{post['id']}-mixed.mp4"
    if len(segs) > 1:
        run(["ffmpeg", "-y", *inputs, "-filter_complex", chain.rstrip(";"), "-map", vl, "-map", al,
             *enc, str(mixed)])
    else:
        shutil.copy(segs[0][0], mixed)

    out = outdir / "reel.mp4"
    if post.get("audio"):  # optional licensed/owned music bed, ducked under the clip sound
        aud = fetch(post["audio"])
        run(["ffmpeg", "-y", "-i", str(mixed), "-i", str(aud), "-filter_complex",
             f"[1:a]atrim=0:{total:.2f},afade=t=in:d=0.4,afade=t=out:st={max(total - 1.2, 0):.2f}:d=1.2,"
             f"volume={post.get('audio_volume', 0.5)}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", str(out)])
    else:
        run(["ffmpeg", "-y", "-i", str(mixed), "-c", "copy", "-movflags", "+faststart", str(out)])

    # cover
    cover = post.get("cover") or {}
    cphoto = fetch(cover["src"]) if cover.get("src") else fetch(post["scenes"][0]["src"])
    if cphoto.suffix.lower() in (".mp4", ".mov", ".webm"):
        frame = tmp / f"{post['id']}-frame.png"
        run(["ffmpeg", "-y", "-ss", "0.5", "-i", str(cphoto), "-frames:v", "1", str(frame)])
        cphoto = frame
    cpng = tmp / f"{post['id']}-cover.png"
    shot(page, render.reel_cover(cover, cphoto, logo), cpng, W, H)
    to_jpeg(cpng, outdir / "cover.jpg")
    return ["reel.mp4"], "cover.jpg"


def build(brief_path: Path):
    brief = json.loads(brief_path.read_text())
    week = brief["week"]
    media_root = ROOT / "docs" / "media" / week
    media_root.mkdir(parents=True, exist_ok=True)
    base = f"{BRAND['media_base_url'].rstrip('/')}/{week}"
    logo = get_logo()
    queue = {"week": week, "generated_from": str(brief_path.relative_to(ROOT)), "posts": []}

    with tempfile.TemporaryDirectory() as td, sync_playwright() as pw:
        tmp = Path(td)
        browser = pw.chromium.launch()
        page = browser.new_page(device_scale_factor=1)
        for post in brief["posts"]:
            log("post", post["id"], post["type"])
            outdir = media_root / post["id"]
            if outdir.exists():
                shutil.rmtree(outdir)
            outdir.mkdir(parents=True)
            entry = {k: post[k] for k in ("id", "date", "type", "pillar", "title") if k in post}
            entry["time"] = post.get("time", brief.get("default_time", "19:30"))
            entry["status"] = post.get("status", "approved")
            if post["type"] in ("image", "carousel"):
                files = build_slides(page, post, outdir, logo, tmp)
                entry["media"] = [f"{base}/{post['id']}/{f}" for f in files]
                entry["files"] = [f"docs/media/{week}/{post['id']}/{f}" for f in files]
            elif post["type"] == "reel":
                files, cover = build_reel(page, post, outdir, logo, tmp)
                entry["media"] = [f"{base}/{post['id']}/{f}" for f in files]
                entry["files"] = [f"docs/media/{week}/{post['id']}/{f}" for f in files]
                entry["cover"] = f"{base}/{post['id']}/{cover}"
                entry["cover_file"] = f"docs/media/{week}/{post['id']}/{cover}"
            else:
                raise ValueError(f"unknown type {post['type']}")
            tags = post.get("hashtags", BRAND["hashtags_default"])
            entry["caption"] = post["caption"].strip() + ("\n\n" + " ".join(tags) if tags else "")
            entry["fb_caption"] = post.get("fb_caption", post["caption"]).strip()
            entry["alt_text"] = post.get("alt_text", "")
            queue["posts"].append(entry)
        browser.close()

    qpath = ROOT / "queue" / f"{week}.json"
    qpath.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n")
    log("wrote", qpath.relative_to(ROOT), "with", len(queue["posts"]), "posts")
    write_preview(queue)


def write_preview(queue: dict):
    """Markdown preview used as the PR comment (images from the branch, videos linked)."""
    lines = [f"## Week {queue['week']} — preview", "",
             "Merge this PR to approve the week. Each post goes live on its date at about 7:45 PM PKT.",
             "To drop a post, set its `status` to `skip` in the queue file before merging.", ""]
    for p in queue["posts"]:
        lines.append(f"### {p['date']} · {p['type'].upper()} · {p.get('title', p['id'])}")
        if p["type"] == "reel":
            lines.append(f"<img src=\"{{RAW}}/{p['cover_file']}\" width=\"240\"> "
                         f"[▶ Watch the Reel]({{BLOB}}/{p['files'][0]})")
        else:
            lines.append(" ".join(f"<img src=\"{{RAW}}/{f}\" width=\"200\">" for f in p["files"]))
        lines += ["", "```text", p["caption"], "```", ""]
    (ROOT / "queue" / f"{queue['week']}.preview.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: build.py briefs/<week>.json")
    build(Path(sys.argv[1]).resolve())
