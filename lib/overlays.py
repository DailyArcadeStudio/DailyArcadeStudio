"""Transparent overlays composited over video and stills.

Showcase scenes put the rotating object on one half of the frame and the
text on the other, so the viewer is always looking at the real thing
while it is being described. Image scenes get a lower-third caption.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from slides import (W, H, FG, MUTED, ACCENT, YELLOW, _font, _split_bold, _wrap)

PANEL = (10, 13, 20)


def _bullets_rgba(d, items, x, y, size=40, gap=28, max_w=760):
    """draw_bullets, but onto an RGBA overlay (same wrapping rules)."""
    f, fb = _font("sans", size), _font("sans_bold", size)
    indent, line_h = 44, int(size * 1.18)
    for it in items:
        my = y + size * 0.30
        d.polygon([(x, my), (x, my + size * 0.42),
                   (x + size * 0.34, my + size * 0.21)], fill=ACCENT + (255,))
        words = []
        for seg, bold in _split_bold(it):
            for w in seg.split(" "):
                if w:
                    words.append((w, bold))
        cx, cy = x + indent, y
        base = cy + size
        for wi, (w, bold) in enumerate(words):
            ff = fb if bold else f
            col = (YELLOW if bold else FG) + (255,)
            piece = w if (wi == 0 or w[0] in ",.:;!?)") else " " + w
            pw = d.textlength(piece, font=ff)
            if cx + pw > x + max_w and cx > x + indent:
                cy += line_h
                base = cy + size
                cx = x + indent
                piece = w
                pw = d.textlength(piece, font=ff)
            d.text((cx, base), piece, font=ff, fill=col, anchor="ls")
            cx += pw
        y = cy + size + gap
    return y


def showcase_overlay(scene):
    """Text panel down the right side; the object keeps the left."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # a soft scrim so text stays readable over the moving object
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(scrim).rectangle((W // 2 - 60, 0, W, H), fill=PANEL + (215,))
    img.alpha_composite(scrim)

    x = W // 2 + 20
    y = 250
    if scene.get("kicker"):
        fk = _font("sans_bold", 32)
        d.text((x, y), scene["kicker"], font=fk, fill=ACCENT + (255,))
        d.rectangle((x, y + 46, x + d.textlength(scene["kicker"], font=fk), y + 49),
                    fill=ACCENT + (255,))
        y += 84
    ft = _font("sans_bold", 62)
    for ln in _wrap(d, scene["title"], ft, 800):
        d.text((x, y), ln, font=ft, fill=FG + (255,))
        y += 76
    y += 30
    _bullets_rgba(d, scene.get("bullets", []), x, y, size=38, gap=28, max_w=790)
    return img


STORY_W = 1180          # width of the story picture, left side of frame


def story_overlay(scene, caption, still_path):
    """Story picture + caption on the left; gameplay shows through on the right.

    The gameplay never stops for a static photo — the picture is inset with
    a soft edge so the running game stays visible beside it.
    """
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    still = Image.open(still_path).convert("RGB")
    # cover STORY_W x H, then centre-crop
    sc = max(STORY_W / still.width, H / still.height)
    still = still.resize((int(still.width * sc) + 1, int(still.height * sc) + 1),
                         Image.LANCZOS)
    left = (still.width - STORY_W) // 2
    top = (still.height - H) // 2
    still = still.crop((left, top, left + STORY_W, top + H)).convert("RGBA")

    # feather the right edge so it blends into the gameplay instead of
    # ending on a hard seam
    mask = Image.new("L", (STORY_W, H), 255)
    md = ImageDraw.Draw(mask)
    for i in range(180):
        md.line([(STORY_W - 180 + i, 0), (STORY_W - 180 + i, H)],
                fill=int(255 * (1 - i / 180)))
    still.putalpha(mask)
    img.alpha_composite(still, (0, 0))

    # caption sits over the picture, bottom-left
    d = ImageDraw.Draw(img)
    f = _font("sans", 44)
    lines = _wrap(d, caption, f, STORY_W - 150)
    band_h = 60 + len(lines) * 58
    grad = Image.new("RGBA", (STORY_W, band_h + 80), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(band_h + 80):
        a = int(236 * min(1.0, i / 80))
        gd.line([(0, i), (STORY_W, i)], fill=PANEL + (a,))
    grad.putalpha(Image.composite(
        grad.getchannel("A"), Image.new("L", grad.size, 0),
        mask.crop((0, 0, STORY_W, band_h + 80))))
    img.alpha_composite(grad, (0, H - band_h - 80))

    y = H - band_h - 4
    for ln in lines:
        d.text((70, y), ln, font=f, fill=FG + (255,))
        y += 58
    return img


def title_card(text, sub=None):
    """Full-frame text over video, used for the opening hook."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font("sans_bold", 92)
    lines = _wrap(d, text, f, int(W * 0.84))
    total = len(lines) * 106
    y = (H - total) // 2
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2 + 3, y + 3), ln, font=f, fill=(0, 0, 0, 200))
        d.text(((W - w) / 2, y), ln, font=f, fill=FG + (255,))
        y += 106
    if sub:
        fs = _font("sans_bold", 46)
        w = d.textlength(sub, font=fs)
        d.text(((W - w) / 2, y + 24), sub, font=fs, fill=ACCENT + (255,))
    return img
