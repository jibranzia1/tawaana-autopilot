# Tawaana content playbook

The rules every weekly batch follows. The weekly generator reads this file first.

## Brand facts (only claim what is here)

- Product: super lightweight iron body with PFOA-free granite non-stick coating, wooden handle with hanging loop.
- Range: Tawa (12", 13", 14"), Fry Pan (20–30cm), Hot Plate (12", 13", 14"), Karahi with glass lid.
- No seasoning needed. Won't rust. Won't warp on high flame. Even, steady heat.
- Works on gas and electric stoves. Dishwasher safe, hand wash recommended.
- 1-year replacement warranty: peeling, cracks, warping, manufacturing defects.
- Never say "cast iron" or "heavy". The line is "Iron, made light." / "super lightweight iron".
- Care rules (from the care guide): low-to-medium flame, preheat 1–2 min; wooden or silicone spatula only; let it cool before washing; soft sponge, no steel wool; dry fully and hang by the loop; a few drops of oil, no aerosol spray; keep the wooden handle away from ovens and open coal.

## What posts are for

Organic only: features and reasons to buy. No prices, discounts, codes, "sale", "limited time" or urgency.
Soft call to action only: "tawaana.com" or "link in bio". Validation warns on salesy words.

## Voice

Warm, confident, desi kitchen. Plain English with short Roman Urdu lines ("Subah ka paratha", "Har ghar ki zaroorat").
Short sentences. One idea per slide. No emoji walls (max 2 per caption). No exclamation spam.

## Weekly mix (7 posts, one a day at 19:30 PKT)

| Day | Format | Pillar |
|---|---|---|
| Mon | Reel | Hero cooking moment (tawa) |
| Tue | Carousel | Why Tawaana / comparisons / myth-busting |
| Wed | Static | Single feature close-up |
| Thu | Reel | Second product in action (fry pan / hot plate / karahi) |
| Fri | Carousel | Care, tips, recipes |
| Sat | Static | Lifestyle / ease of use / gifting (no offers) |
| Sun | Reel | Family meal / weekend cooking |

Rotate products across weeks so each gets at least one hero moment a fortnight.

## Visual rules

- Generate with Higgsfield, always passing the real product photo as a reference so the cookware matches the store:
  tawa `tw2-product-tawa.png`, fry pan `tw2-product-frypan.png`, karahi `tw2-product-karahi.png`, hot plate `tw2-product-hotplate.png` (tawaana.com/cdn/shop/files/).
- Images: `nano_banana_2_1`, 2k. Feed 4:5, Reel frames 9:16. Prompts say "no text, no logos" — all text is added by the renderer.
- Reel clips: `kling3_0`, pro, 5s, 9:16, sound on (natural sizzle/steam, "no music, no speech"). 3 clips per Reel + end card.
- Hands are fine; avoid faces (AI faces read fake).
- Warm light, real Pakistani home kitchen, food looks hot and fresh.
- Leave empty space where the text goes (top third for covers, bottom for text slides).

## Brief format

`briefs/<YYYY>-W<ww>.json` on branch `week/<YYYY>-W<ww>`:

```json
{
  "week": "2026-W45",
  "default_time": "19:30",
  "posts": [
    {"id": "2026-11-02-paratha-reel", "date": "2026-11-02", "type": "reel", "pillar": "hero", "title": "...",
     "scenes": [{"src": "<clip url>", "kicker": "...", "text": "Headline with *copper italic*", "sub": "...",
                 "position": "lower|upper", "duration": 4.6}],
     "end_card": {"headline": "...", "sub": "..."},
     "cover": {"src": "<image url>", "kicker": "...", "headline": "..."},
     "caption": "...", "hashtags": ["#Tawaana", "..."]},
    {"id": "...", "type": "carousel", "slides": [
       {"src": "<image url>", "layout": "cover|text|table|closing", "kicker": "", "headline": "", "body": "",
        "number": "01", "table": {"cols": ["", "Tawaana", "A", "B"], "rows": [["Row", "yes", "no", "yes"]]}}]},
    {"id": "...", "type": "image", "slides": [{"src": "...", "layout": "cover", "...": "..."}]}
  ]
}
```

`*word*` renders in copper italic. `\n` breaks a line. Captions: hook line first, 3–6 short lines, soft CTA, hashtags are appended from the `hashtags` list (5–8 tags).
