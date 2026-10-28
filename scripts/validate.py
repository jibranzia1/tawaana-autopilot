"""Check queue files and built media against Instagram / Facebook publishing rules.

    python scripts/validate.py              # all queue/*.json
    python scripts/validate.py queue/2026-W45.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
BANNED = [  # keep organic content non-salesy, per brand rules
    r"\bsale\b", r"\bdiscount\b", r"\b\d+\s?% off\b", r"\bcoupon\b", r"\bpromo code\b", r"\blimited time\b",
    r"\bRs\.?\s?\d", r"\bPKR\b", r"\bcast iron\b",
]


def probe(p: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def check_post(p: dict, errs: list[str], warns: list[str]):
    pid = p.get("id", "?")
    for k in ("id", "date", "type", "caption", "media", "files"):
        if k not in p:
            errs.append(f"{pid}: missing '{k}'")
            return
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["date"]):
        errs.append(f"{pid}: bad date {p['date']}")
    cap = p["caption"]
    if len(cap) > 2200:
        errs.append(f"{pid}: caption {len(cap)} chars (IG max 2200)")
    if cap.count("#") > 30:
        errs.append(f"{pid}: more than 30 hashtags")
    for pat in BANNED:
        if re.search(pat, cap, re.I):
            warns.append(f"{pid}: caption matches banned pattern {pat!r} (organic posts stay non-salesy)")
    if len(p["media"]) != len(p["files"]):
        errs.append(f"{pid}: media/files length mismatch")
    if p["type"] == "carousel" and not 2 <= len(p["files"]) <= 10:
        errs.append(f"{pid}: carousel needs 2-10 slides")
    for f in p["files"] + ([p["cover_file"]] if p.get("cover_file") else []):
        path = ROOT / f
        if not path.exists():
            errs.append(f"{pid}: missing file {f}")
            continue
        if path.suffix == ".jpg":
            im = Image.open(path)
            w, h = im.size
            if im.format != "JPEG":
                errs.append(f"{pid}: {f} is not JPEG")
            if path.stat().st_size > 8 * 1024 * 1024:
                errs.append(f"{pid}: {f} over 8MB")
            r = w / h
            if "cover" not in f and not (0.8 - 1e-3 <= r <= 1.91):
                errs.append(f"{pid}: {f} aspect {w}x{h} outside IG feed range")
        elif path.suffix == ".mp4":
            info = probe(path)
            v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
            a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
            dur = float(info["format"]["duration"])
            if not v or v["codec_name"] != "h264":
                errs.append(f"{pid}: reel video must be H.264")
            elif (v["width"], v["height"]) != (1080, 1920):
                errs.append(f"{pid}: reel is {v['width']}x{v['height']}, expected 1080x1920")
            if not a or a["codec_name"] != "aac":
                errs.append(f"{pid}: reel audio must be AAC")
            if not 3 <= dur <= 90:
                errs.append(f"{pid}: reel duration {dur:.1f}s outside 3-90s")
            if path.stat().st_size > 100 * 1024 * 1024:
                errs.append(f"{pid}: reel over 100MB")


def main():
    files = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "queue").glob("*.json"))
    errs, warns, dates = [], [], {}
    for q in files:
        data = json.loads(Path(q).read_text())
        for p in data.get("posts", []):
            check_post(p, errs, warns)
            if p.get("status", "approved") == "approved":
                key = (p.get("date"), p.get("time"))
                if key in dates:
                    warns.append(f"{p['id']}: same date/time as {dates[key]}")
                dates[key] = p["id"]
    for w in warns:
        print("WARN ", w)
    for e in errs:
        print("ERROR", e)
    print(f"checked {len(files)} queue file(s): {len(errs)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
