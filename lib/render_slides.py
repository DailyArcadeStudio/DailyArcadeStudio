"""Render the Ninja Dash slide deck to PNGs.

Reuses the Algo-Gym slide engine (lib/slides.py). Scenes carrying a
"clip" key are gameplay footage and get no slide — assemble.py splices
the recording in at that point instead.

usage: python lib/render_slides.py scenes.json out_dir
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slides
from slides import (W, H, FG, MUTED, ACCENT, YELLOW, base_canvas, draw_kicker,
                    draw_title, draw_bullets, draw_code_panel, _font, _wrap)


def render_hero(scene):
    """Big centered card — used for the title and the outro."""
    img, d = base_canvas()
    bullets = scene.get("bullets", [])
    f = _font("sans_bold", 116)
    lines = _wrap(d, scene["title"], f, int(W * 0.82))

    # sit the block higher when bullets follow, so the two don't crowd
    block_h = len(lines) * 132
    y = (390 if bullets else H // 2 - block_h // 2 - 40)
    if scene.get("kicker"):
        fk = _font("sans_bold", 34)
        kw = d.textlength(scene["kicker"], font=fk)
        d.text(((W - kw) / 2, y - 70), scene["kicker"], font=fk, fill=ACCENT)
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y), ln, font=f, fill=FG)
        y += 132

    sub = scene.get("subtitle")
    if sub:
        fs = _font("sans_bold", 60)
        w = d.textlength(sub, font=fs)
        d.text(((W - w) / 2, y + 30), sub, font=fs, fill=ACCENT)
    if bullets:
        draw_bullets(d, bullets, 430, y + 60, size=44, gap=30, max_w=1200)
    return img


def render_slide(scene):
    if scene["kind"] in ("title", "outro"):
        return render_hero(scene)

    img, d = base_canvas()
    if scene.get("kicker"):
        draw_kicker(d, scene["kicker"], 120, 90)
    draw_title(d, scene["title"], 120, 150, size=72)

    code = scene.get("code")
    bullets = scene.get("bullets", [])
    if code:
        draw_code_panel(d, img, code, 120, 310, 1080, 650,
                        title=scene.get("code_title", "game.js"))
        if bullets:
            draw_bullets(d, bullets, 1260, 350, size=38, gap=30, max_w=600)
    elif bullets:
        size, gap = (54, 44) if len(bullets) <= 3 else (46, 34)
        draw_bullets(d, bullets, 140, 360, size=size, gap=gap, max_w=1620)
    return img


def main(scenes_path, out_dir):
    data = json.loads(Path(scenes_path).read_text())
    slides.set_lang(data.get("lang", "python"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    made = []
    for i, sc in enumerate(data["scenes"]):
        if sc.get("clip"):
            made.append((i, sc["kind"], "clip:" + sc["clip"]))
            continue
        png = out / f"s{i:02d}_{sc['kind']}.png"
        render_slide(sc).save(png)
        made.append((i, sc["kind"], str(png)))

    for i, kind, what in made:
        print(f"{i:2d} {kind:12s} {what}")
    print(f"SLIDES_OK {sum(1 for _,_,w in made if not w.startswith('clip:'))} rendered")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
