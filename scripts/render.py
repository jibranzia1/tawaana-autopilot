"""HTML templates for Tawaana feed slides, Reel text overlays, covers and end cards.

Everything is rendered with a headless Chromium (Playwright) so the brand fonts and
spelling are exact. AI images never carry text; all text is added here.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "assets" / "fonts"
BRAND = json.loads((ROOT / "config" / "brand.json").read_text())
C = BRAND["colors"]

FEED_W, FEED_H = 1080, 1350
REEL_W, REEL_H = 1080, 1920


def esc(s: str | None) -> str:
    """Escape text and allow *word* for copper italic emphasis and \n for line breaks."""
    if not s:
        return ""
    out = html.escape(s)
    parts = out.split("*")
    for i in range(1, len(parts), 2):
        parts[i] = f'<em>{parts[i]}</em>'
    return "".join(parts).replace("\n", "<br>")


def _base_css(w: int, h: int, transparent: bool = False) -> str:
    bg = "transparent" if transparent else C["iron"]
    return f"""
@font-face {{ font-family: 'Playfair Display'; src: url('file://{FONTS}/PlayfairDisplay.ttf'); font-weight: 400 900; }}
@font-face {{ font-family: 'Playfair Display'; src: url('file://{FONTS}/PlayfairDisplay-Italic.ttf'); font-style: italic; font-weight: 400 900; }}
@font-face {{ font-family: 'Jost'; src: url('file://{FONTS}/Jost.ttf'); font-weight: 100 900; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {w}px; height: {h}px; background: {bg}; overflow: hidden; }}
body {{ font-family: 'Jost', sans-serif; color: {C['cream']}; -webkit-font-smoothing: antialiased; }}
.frame {{ position: relative; width: {w}px; height: {h}px; overflow: hidden; }}
.photo {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.kicker {{ font-family: 'Jost'; font-weight: 500; font-size: 26px; letter-spacing: 0.32em; text-transform: uppercase; color: {C['ember']}; }}
.headline {{ font-family: 'Playfair Display'; font-weight: 500; color: {C['cream']}; letter-spacing: -0.015em; line-height: 1.06; text-wrap: balance; }}
.headline em {{ font-style: italic; color: {C['ember']}; }}
.body {{ font-family: 'Jost'; font-weight: 400; color: {C['cream']}; opacity: 0.9; line-height: 1.42; text-wrap: pretty; }}
.body em {{ font-style: normal; color: {C['ember']}; font-weight: 500; }}
.mark {{ display: flex; align-items: center; gap: 14px; }}
.mark img {{ height: 46px; width: auto; }}
.wordmark {{ font-family: 'Jost'; font-size: 30px; letter-spacing: 0.24em; color: {C['cream']}; }}
.wordmark b {{ font-weight: 700; }} .wordmark span {{ font-weight: 300; color: {C['copper']}; }}
.rule {{ width: 72px; height: 3px; background: {C['copper']}; border-radius: 2px; }}
"""


def _mark(logo: Path | None, height: int = 46) -> str:
    if logo and logo.exists():
        return f'<div class="mark"><img src="file://{logo}" style="height:{height}px"></div>'
    return '<div class="mark"><div class="wordmark"><b>TAWA</b><span>ANA</span></div></div>'


def _doc(css: str, inner: str) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{inner}</body></html>"


# ---------------------------------------------------------------- feed slides (4:5)

def feed_slide(slide: dict, photo: Path | None, logo: Path | None, index: int, total: int) -> str:
    layout = slide.get("layout", "cover")
    css = _base_css(FEED_W, FEED_H)
    img = f'<img class="photo" src="file://{photo}">' if photo else ""
    swipe = ""
    if total > 1 and index < total:
        swipe = (f'<div style="position:absolute;right:64px;bottom:58px;font:500 22px Jost;letter-spacing:.2em;'
                 f'color:{C["cream"]};opacity:.75">{index:02d} / {total:02d} &nbsp;→</div>')
    elif total > 1:
        swipe = (f'<div style="position:absolute;right:64px;bottom:58px;font:500 22px Jost;letter-spacing:.2em;'
                 f'color:{C["cream"]};opacity:.75">{index:02d} / {total:02d}</div>')

    if layout == "cover":
        inner = f"""
<div class="frame">{img}
  <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,10,9,.88) 0%,rgba(11,10,9,.55) 34%,rgba(11,10,9,0) 58%,rgba(11,10,9,.35) 100%)"></div>
  <div style="position:absolute;left:72px;right:72px;top:84px">
    <div class="kicker">{esc(slide.get('kicker'))}</div>
    <div class="headline" style="font-size:{slide.get('size', 88)}px;margin-top:26px">{esc(slide.get('headline'))}</div>
    <div class="body" style="font-size:34px;margin-top:26px;max-width:820px">{esc(slide.get('body'))}</div>
  </div>
  <div style="position:absolute;left:72px;bottom:52px">{_mark(logo, 40)}</div>
  {swipe}
</div>"""

    elif layout == "text":
        num = slide.get("number")
        badge = (f'<div style="font:500 italic 120px \'Playfair Display\';color:{C["copper"]};line-height:.9">{esc(num)}</div>'
                 if num else "")
        inner = f"""
<div class="frame">{img}
  <div style="position:absolute;inset:0;background:linear-gradient(0deg,rgba(11,10,9,.94) 0%,rgba(11,10,9,.82) 30%,rgba(11,10,9,0) 62%)"></div>
  <div style="position:absolute;left:72px;right:72px;bottom:130px">
    {badge}
    <div class="kicker" style="margin-top:14px">{esc(slide.get('kicker'))}</div>
    <div class="headline" style="font-size:{slide.get('size', 66)}px;margin-top:18px">{esc(slide.get('headline'))}</div>
    <div class="body" style="font-size:33px;margin-top:22px;max-width:880px">{esc(slide.get('body'))}</div>
  </div>
  <div style="position:absolute;left:72px;bottom:52px">{_mark(logo, 34)}</div>
  {swipe}
</div>"""

    elif layout == "table":
        t = slide["table"]
        cols = t["cols"]
        head = "".join(
            f'<th style="font:{"600" if i == 1 else "400"} 26px Jost;letter-spacing:.06em;'
            f'color:{C["ember"] if i == 1 else C["ash"]};padding:0 8px 20px;text-align:center">{esc(c)}</th>'
            for i, c in enumerate(cols) if i > 0)
        rows = ""
        for r in t["rows"]:
            cells = ""
            for i, v in enumerate(r[1:], start=1):
                if v in ("yes", "✓"):
                    sym = f'<span style="color:{C["copper"] if i == 1 else C["cream"]};font-size:40px">✓</span>'
                elif v in ("no", "✕"):
                    sym = f'<span style="color:#9A9187;font-size:34px">✕</span>'
                else:
                    sym = f'<span style="color:{C["ash"]};font-size:24px">{esc(v)}</span>'
                bg = "background:rgba(192,122,69,.10);" if i == 1 else ""
                cells += f'<td style="text-align:center;padding:20px 8px;{bg}">{sym}</td>'
            rows += (f'<tr style="border-top:1px solid rgba(242,235,225,.10)"><td style="font:400 29px Jost;'
                     f'color:{C["cream"]};padding:20px 0">{esc(r[0])}</td>{cells}</tr>')
        bgphoto = (f'<img class="photo" src="file://{photo}" style="opacity:.16;filter:blur(6px) saturate(.6)">'
                   if photo else "")
        inner = f"""
<div class="frame" style="background:{C['iron']}">{bgphoto}
  <div style="position:absolute;left:72px;right:72px;top:84px">
    <div class="kicker">{esc(slide.get('kicker'))}</div>
    <div class="headline" style="font-size:{slide.get('size', 64)}px;margin-top:22px">{esc(slide.get('headline'))}</div>
    <table style="width:100%;border-collapse:collapse;margin-top:52px">
      <tr><th style="text-align:left;width:46%"></th>{head}</tr>{rows}
    </table>
  </div>
  <div style="position:absolute;left:72px;bottom:52px">{_mark(logo, 34)}</div>
  {swipe}
</div>"""

    elif layout == "closing":
        bgphoto = (f'<img class="photo" src="file://{photo}" style="opacity:.28">'
                   f'<div style="position:absolute;inset:0;background:radial-gradient(ellipse at center,rgba(18,17,16,.55) 0%,rgba(11,10,9,.95) 75%)"></div>'
                   if photo else "")
        inner = f"""
<div class="frame" style="background:{C['iron']}">{bgphoto}
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 110px">
    {_mark(logo, 74)}
    <div class="rule" style="margin:48px auto 44px"></div>
    <div class="headline" style="font-size:{slide.get('size', 70)}px">{esc(slide.get('headline'))}</div>
    <div class="body" style="font-size:34px;margin-top:28px">{esc(slide.get('body'))}</div>
    <div style="font:500 28px Jost;letter-spacing:.28em;color:{C['ember']};margin-top:56px">{esc(slide.get('footer', BRAND['website'].upper()))}</div>
  </div>
  {swipe}
</div>"""
    else:
        raise ValueError(f"unknown layout {layout}")
    return _doc(css, inner)


# ---------------------------------------------------------------- reels (9:16)

def reel_overlay(scene: dict) -> str:
    """Transparent 1080x1920 overlay with the scene's on-screen text, inside IG safe zones."""
    css = _base_css(REEL_W, REEL_H, transparent=True)
    pos = scene.get("position", "lower")
    top = 300 if pos == "upper" else None
    place = f"top:{top}px" if top else "bottom:560px"
    shade = ("linear-gradient(180deg,rgba(11,10,9,.86) 0%,rgba(11,10,9,.70) 22%,rgba(11,10,9,.35) 34%,rgba(11,10,9,0) 46%)" if pos == "upper"
             else "linear-gradient(0deg,rgba(11,10,9,.88) 0%,rgba(11,10,9,.78) 30%,rgba(11,10,9,.55) 44%,rgba(11,10,9,0) 64%)")
    inner = f"""
<div class="frame">
  <div style="position:absolute;inset:0;background:{shade}"></div>
  <div style="position:absolute;left:84px;right:84px;{place};text-shadow:0 2px 18px rgba(0,0,0,.75),0 0 4px rgba(0,0,0,.5)">
    <div class="kicker" style="font-size:32px;font-weight:600;color:#E8A272">{esc(scene.get('kicker'))}</div>
    <div class="headline" style="font-size:{scene.get('size', 86)}px;margin-top:20px">{esc(scene.get('text'))}</div>
    <div class="body" style="font-size:38px;margin-top:20px">{esc(scene.get('sub'))}</div>
  </div>
</div>"""
    return _doc(css, inner)


def reel_end_card(card: dict, logo: Path | None, photo: Path | None = None) -> str:
    css = _base_css(REEL_W, REEL_H)
    bgphoto = (f'<img class="photo" src="file://{photo}" style="opacity:.22;filter:blur(3px)">' if photo else "")
    inner = f"""
<div class="frame" style="background:radial-gradient(ellipse at 50% 42%,#221d19 0%,{C['deep_iron']} 70%)">{bgphoto}
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 110px 120px">
    {_mark(logo, 96)}
    <div class="rule" style="margin:56px auto 52px;width:90px"></div>
    <div class="headline" style="font-size:{card.get('size', 84)}px">{esc(card.get('headline'))}</div>
    <div class="body" style="font-size:40px;margin-top:30px">{esc(card.get('sub'))}</div>
    <div style="font:500 32px Jost;letter-spacing:.3em;color:{C['ember']};margin-top:70px">{esc(card.get('footer', BRAND['website'].upper()))}</div>
  </div>
</div>"""
    return _doc(css, inner)


def reel_cover(cover: dict, photo: Path, logo: Path | None) -> str:
    """Reel cover (9:16). Key text sits in the centre 4:5 crop so it reads in the profile grid."""
    css = _base_css(REEL_W, REEL_H)
    inner = f"""
<div class="frame"><img class="photo" src="file://{photo}">
  <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,10,9,0) 20%,rgba(11,10,9,.80) 48%,rgba(11,10,9,.80) 62%,rgba(11,10,9,0) 82%)"></div>
  <div style="position:absolute;left:90px;right:90px;top:760px;text-align:center">
    <div class="kicker" style="font-size:28px">{esc(cover.get('kicker'))}</div>
    <div class="headline" style="font-size:{cover.get('size', 96)}px;margin-top:22px">{esc(cover.get('headline'))}</div>
  </div>
  <div style="position:absolute;left:0;right:0;top:1290px;display:flex;justify-content:center">{_mark(logo, 44)}</div>
</div>"""
    return _doc(css, inner)
