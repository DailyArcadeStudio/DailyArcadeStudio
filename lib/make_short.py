"""45-second vertical short: the event highlights, back to back.

The gameplay is 16:9, so it is letterboxed into 1080x1920 with a PIL
band above (the point) and below (the game name). Each beat is cut
straight out of the same screen recording the main video uses.

usage: python lib/make_short.py work_dir out.mp4
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from slides import _font, _wrap, FG, YELLOW, ACCENT

SW, SH = 1080, 1920
FPS = 30
# Crop the 16:9 gameplay to 4:3 and scale it up: the action sits in the
# middle of frame, so trimming the sides buys a much bigger picture.
VID_W, VID_H = SW, 810
VID_TOP = 940 - VID_H // 2



# Fallback beats. A game supplies its own via scenes.json "short":
#   [{"mark": "...", "lead": -0.5, "dur": 7.0, "headline": "..."}, ...]
BEATS = [
    ("surge",    -0.5, 7.0, "The road speeds up"),
    ("wall",     -0.5, 7.0, "Two lanes slam shut"),
    ("blackout", -0.5, 6.5, "Then the lights go out"),
    ("boss",     -0.3, 9.0, "And this comes up behind you"),
    ("death",    -2.0, 9.5, "Every run ends the same way"),
]


def load_beats(slug):
    """A game's own short beats, when its storyboard defines them."""
    if not slug:
        return BEATS
    f = Path(__file__).resolve().parent.parent / "games" / slug / "scenes.json"
    if not f.exists():
        return BEATS
    spec = json.loads(f.read_text()).get("short")
    if not spec:
        return BEATS
    return [(b["mark"], b.get("lead", -0.5), b.get("dur", 7.0), b["headline"])
            for b in spec]


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def band(headline, dst, title="NINJA DASH"):
    """Top headline + bottom game name, transparent in the middle."""
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, SW, VID_TOP), fill=(8, 11, 17, 255))
    d.rectangle((0, VID_TOP + VID_H, SW, SH), fill=(8, 11, 17, 255))

    f = _font("sans_bold", 76)
    lines = _wrap(d, headline, f, SW - 120)
    y = VID_TOP - 40 - len(lines) * 92
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((SW - w) / 2, y), ln, font=f, fill=YELLOW + (255,))
        y += 92

    fn = _font("sans_bold", 78)
    name = title
    w = d.textlength(name, font=fn)
    d.text(((SW - w) / 2, VID_TOP + VID_H + 60), name, font=fn, fill=FG + (255,))
    fs = _font("sans", 42)
    sub = "link in the description"
    w = d.textlength(sub, font=fs)
    d.text(((SW - w) / 2, VID_TOP + VID_H + 160), sub, font=fs, fill=ACCENT + (255,))
    img.save(dst)


def main(work_dir, out_path):
    work = Path(work_dir)
    tmp = work / "short"
    tmp.mkdir(parents=True, exist_ok=True)
    raw = work / "raw.mp4"
    marks = {n: t for n, t in json.loads((work / "marks.json").read_text())["marks"]}
    slug = os.environ.get("GAME_SLUG")
    title = os.environ.get("GAME_TITLE", "NINJA DASH")
    beats = [b for b in load_beats(slug) if b[0] in marks]

    segs = []
    for i, (mark, lead, dur, headline) in enumerate(beats):
        ov = tmp / f"band{i}.png"
        band(headline, ov, title)
        seg = tmp / f"seg{i}.mp4"
        # scale so the crop box is filled in both axes, then take the centre
        fc = (f"color=c=black:s={SW}x{SH}:r={FPS}[base];"
              f"[0:v]scale={VID_W}:{VID_H}:force_original_aspect_ratio=increase,"
              f"crop={VID_W}:{VID_H}[vid];"
              f"[base][vid]overlay=0:{VID_TOP}[tmp];"
              f"[tmp][1:v]overlay=0:0[v]")
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-ss", f"{max(marks[mark] + lead, 0):.3f}", "-i", str(raw),
             "-loop", "1", "-i", str(ov),
             "-filter_complex", fc, "-map", "[v]",
             "-t", f"{dur:.3f}", "-r", str(FPS),
             "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "medium",
             "-crf", "20", "-an", str(seg)])
        segs.append(seg)
        print(f"  beat{i} {mark:9s} {dur:4.1f}s  {headline}", flush=True)

    lst = tmp / "list.txt"
    lst.write_text("\n".join(f"file '{s.resolve()}'" for s in segs))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(out_path)])
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1",
                        str(out_path)], capture_output=True, text=True).stdout.strip()
    print(f"SHORT_OK {out_path} {float(d):.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
