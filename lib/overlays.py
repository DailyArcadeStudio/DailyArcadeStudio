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


def image_overlay(scene, caption):
    """Lower third over an SDXL still, for the story beats."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font("sans", 50)
    lines = _wrap(d, caption, f, int(W * 0.80))
    band_h = 70 + len(lines) * 64
    grad = Image.new("RGBA", (W, band_h + 90), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(band_h + 90):          # fade the band into the picture
        a = int(232 * min(1.0, i / 90))
        gd.line([(0, i), (W, i)], fill=PANEL + (a,))
    img.alpha_composite(grad, (0, H - band_h - 90))

    y = H - band_h - 10
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y), ln, font=f, fill=FG + (255,))
        y += 64
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
