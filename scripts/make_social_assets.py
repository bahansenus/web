#!/usr/bin/env python3
"""Generate the social/favicon image set from assets/logo.jpg.

Outputs (committed, so CI does not need Pillow):
  assets/favicon-192.png      192x192  shield mark, for <link rel="icon">
  assets/apple-touch-icon.png 180x180  same mark, cream background
  assets/og-card.png          1200x630 Open Graph / NewsArticle share card

The logo is a 1600x396 banner: a near-square shield mark on the left ~21% and
the B.A. HANSEN wordmark to its right. The mark is cropped out by scanning for
its ink rather than hard-coding a box, so re-cutting the logo does not silently
produce an off-centre icon.

Run: python3 scripts/make_social_assets.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"
LOGO = ASSETS / "logo.jpg"

CREAM = (241, 238, 229)
INK = (30, 34, 40)
MUTED = (74, 84, 104)
ACCENT = (56, 189, 248)      # --accent in style.css
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _fit(draw, text, font_path, start, max_w, floor=18):
    """Largest font size <= start whose rendered text fits max_w."""
    size = start
    while size > floor:
        f = ImageFont.truetype(font_path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(font_path, floor)


def mark_box(img: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box of the shield mark: the FIRST column-run of ink.

    The logo is mark + wordmark side by side, so a plain bounding box of the
    left quarter swallows the neighbouring 'B.A.' glyphs. This walks columns
    from the left edge and stops at the first real gap, which isolates the mark.
    """
    w, h = img.size
    win = img.crop((0, 0, int(w * 0.30), h)).convert("RGB")
    px = win.load()
    ww = win.size[0]

    inked = []
    for x in range(ww):
        hit = False
        for y in range(0, h, 2):          # every 2nd row is enough to detect ink
            r, g, b = px[x, y]
            if r + g + b < 620:           # noticeably darker than the cream field
                hit = True
                break
        inked.append(hit)

    # first run of inked columns, allowing a 6px tolerance for internal gaps
    start = next((i for i, v in enumerate(inked) if v), None)
    if start is None:
        raise SystemExit("could not locate the shield mark in the logo")
    gap = 0
    end = start
    for x in range(start, ww):
        if inked[x]:
            end = x
            gap = 0
        else:
            gap += 1
            if gap > 6:
                break
    xs = range(start, end + 1)

    ys = []
    for y in range(h):
        for x in xs:
            r, g, b = px[x, y]
            if r + g + b < 620:
                ys.append(y)
                break
    pad = 6
    return (max(start - pad, 0), max(min(ys) - pad, 0),
            min(end + pad, ww), min(max(ys) + pad, h))


def square(img: Image.Image, box, size: int, bg=CREAM) -> Image.Image:
    """Crop box, pad to a square on bg, resize to size x size."""
    crop = img.crop(box)
    side = max(crop.size)
    canvas = Image.new("RGB", (side, side), bg)
    canvas.paste(crop, ((side - crop.size[0]) // 2, (side - crop.size[1]) // 2))
    return canvas.resize((size, size), Image.LANCZOS)


def paste_feathered(dst: Image.Image, icon: Image.Image, xy, feather: int = 7) -> None:
    """Paste icon with a feathered edge so the cream logo field does not show
    as a visible brighter box against the (slightly textured) card background."""
    mask = Image.new("L", icon.size, 0)
    md = ImageDraw.Draw(mask)
    inset = feather
    md.rounded_rectangle([inset, inset, icon.size[0] - inset - 1,
                          icon.size[1] - inset - 1],
                         radius=max(4, icon.size[0] // 8), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(feather / 2))
    dst.paste(icon, xy, mask)


def main() -> None:
    logo = Image.open(LOGO).convert("RGB")

    # ---- icons -------------------------------------------------------------
    mb = mark_box(logo)
    print(f"shield mark bbox: {mb}")
    square(logo, mb, 192).save(ASSETS / "favicon-192.png", optimize=True)
    square(logo, mb, 180).save(ASSETS / "apple-touch-icon.png", optimize=True)

    # ---- Open Graph card ---------------------------------------------------
    W, H = 1200, 630
    card = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(card)

    # shield mark, top-left (feathered so the logo's cream field does not show)
    icon = square(logo, mb, 132)
    paste_feathered(card, icon, (72, 64))

    # wordmark beside it
    f_word = ImageFont.truetype(FONT_B, 54)
    d.text((226, 96), "B.A. HANSEN", font=f_word, fill=INK)
    f_sub = ImageFont.truetype(FONT_R, 26)
    d.text((230, 156), "Architecting Trust", font=f_sub, fill=MUTED)

    # accent rule
    d.rectangle([72, 262, 156, 268], fill=ACCENT)

    # headline + tagline, shrunk to fit
    head = "Daily Security Intelligence Briefing"
    f_head = _fit(d, head, FONT_B, 58, W - 144)
    d.text((72, 302), head, font=f_head, fill=INK)

    line2 = "Tiered threat intelligence for operators — published every morning."
    f_l2 = _fit(d, line2, FONT_R, 32, W - 144)
    d.text((72, 302 + f_head.size + 22), line2, font=f_l2, fill=MUTED)

    # footer, separated by a hairline so the lower third is not dead space
    d.rectangle([72, H - 148, W - 72, H - 147], fill=(216, 210, 196))
    f_foot = ImageFont.truetype(FONT_M, 24)
    d.text((72, H - 110), "bahansen.us", font=f_foot, fill=INK)
    right = "threats · vulnerabilities · supply chain"
    d.text((W - 72 - d.textlength(right, font=f_foot), H - 110), right,
           font=f_foot, fill=MUTED)

    card.save(ASSETS / "og-card.png", optimize=True)
    for n in ("favicon-192.png", "apple-touch-icon.png", "og-card.png"):
        p = ASSETS / n
        print(f"  wrote {p.relative_to(REPO)}  {p.stat().st_size} B")


if __name__ == "__main__":
    main()
