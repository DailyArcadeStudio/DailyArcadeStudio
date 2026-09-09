"""Thumbnails for a game: 1280x720 for the main video, 1080x1920 for the short.

The background is a real frame from the game, darkened, with a short hook
phrase over it in very large type. The phrase says what the game *is* —
a thumbnail has about one second to land, so it never carries a sentence.

usage: python lib/make_thumbnail.py <slug> <work_dir> [out_dir]
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/fukushimatakumi/develop")
from thumb_text import fit_lines      # 全チャンネル共通のタイトル自動フィット
from slides import _font, FG, YELLOW, ACCENT

ROOT = Path(__file__).resolve().parent.parent
TW, TH = 1280, 720          # main
SW, SH = 1080, 1920         # short


def grab(video, at, size):
    """Pull one frame from the recording, covering `size`."""
    tmp = Path("/tmp/_thumb_frame.png")
    w, h = size
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}",
                    "-i", str(video), "-frames:v", "1",
                    "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                           f"crop={w}:{h}", str(tmp)], check=True)
    return Image.open(tmp).convert("RGB")


def stage(img, blur=0.8, lift=1.45):
    """Prepare the game frame as a background.

    The game is a night scene, so veiling it further just yields a black
    rectangle. Brighten and saturate it instead, and rely on the heavy
    text stroke for contrast.
    """
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    img = ImageEnhance.Brightness(img).enhance(lift)
    img = ImageEnhance.Color(img).enhance(1.35)
    return img


def scrim(img, box, strength=0.72):
    """Darken just the band the text sits in, so the rest stays visible."""
    x0, y0, x1, y1 = box
    band = img.crop(box)
    veil = Image.new("RGB", band.size, (5, 7, 12))
    img.paste(Image.blend(band, veil, strength), (x0, y0))
    return img


def fit_font(d, text, size_start, max_w, min_size=44, kind="sans_bold"):
    s = size_start
    while s > min_size:
        f = _font(kind, s)
        if d.textlength(text, font=f) <= max_w:
            return f
        s -= 4
    return _font(kind, min_size)


def stroked(d, xy, text, font, fill, stroke=(0, 0, 0), width=8):
    d.text(xy, text, font=font, fill=fill, stroke_width=width, stroke_fill=stroke)


def wrap_words(d, text, font, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_main(hook, sub, frame, dst):
    img = stage(frame.resize((TW, TH)))
    d = ImageDraw.Draw(img)

    f, lines, lh = fit_lines(d, lambda sz: _font("sans_bold", sz), hook.upper(),
                             TW - 120, TH * 0.46, max_lines=2, hi=150, lo=56)
    total = len(lines) * lh
    y = 96                                  # sit high, leave the track visible
    scrim(img, (0, y - 40, TW, y + total + 130))
    d = ImageDraw.Draw(img)
    for ln in lines:
        w = d.textlength(ln, font=f)
        stroked(d, ((TW - w) / 2, y), ln, f, YELLOW, width=max(7, int(f.size*.07)))
        y += lh

    if sub:
        fs = fit_font(d, sub, 54, TW - 200, 34)
        w = d.textlength(sub, font=fs)
        stroked(d, ((TW - w) / 2, y + 18), sub, fs, FG, width=6)

    # a thin accent rule so it reads as a series, not a one-off
    d.rectangle((0, TH - 12, TW, TH), fill=ACCENT)
    img.save(dst)
    return dst


def make_short(hook, title, frame, dst):
    img = stage(frame.resize((SW, SH)))
    d = ImageDraw.Draw(img)

    f, lines, lh = fit_lines(d, lambda sz: _font("sans_bold", sz), hook.upper(),
                             SW - 90, 620, max_lines=2, hi=190, lo=72)
    y = 300
    scrim(img, (0, y - 60, SW, y + len(lines) * lh + 60))
    scrim(img, (0, SH - 460, SW, SH - 250))
    d = ImageDraw.Draw(img)
    for ln in lines:
        w = d.textlength(ln, font=f)
        stroked(d, ((SW - w) / 2, y), ln, f, YELLOW, width=max(8, int(f.size*.07)))
        y += lh

    fn = fit_font(d, title.upper(), 82, SW - 120, 48)
    w = d.textlength(title.upper(), font=fn)
    stroked(d, ((SW - w) / 2, SH - 380), title.upper(), fn, FG, width=8)
    img.save(dst)
    return dst


def main(slug, work_dir, out_dir=None):
    work = Path(work_dir)
    out = Path(out_dir or ROOT / "output")
    out.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((ROOT / "games" / slug / "scenes.json").read_text())
    title = scenes.get("title", slug)
    thumb = scenes.get("thumb", {})
    hook = thumb.get("hook", title)
    sub = thumb.get("sub", "")

    # pick a frame with something happening: the marks file knows where
    marks = {n: t for n, t in json.loads((work / "marks.json").read_text())["marks"]}
    at = marks.get(thumb.get("frame_mark", "boss"), marks.get("run_start", 2)) + \
        thumb.get("frame_lead", 0.6)

    raw = work / "raw.mp4"
    m = make_main(hook, sub, grab(raw, at, (TW, TH)), out / f"thumb_{slug}.png")
    s = make_short(hook, title, grab(raw, at, (SW, SH)), out / f"sthumb_{slug}.png")
    print(f"THUMB_OK {m}")
    print(f"STHUMB_OK {s}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
