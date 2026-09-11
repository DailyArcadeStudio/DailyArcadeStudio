"""歴史シミュレータの結末画像を作る。

SDXL は文字を描けないので**絵だけ**を生成し、結末名は PIL で重ねる。

    python make_sim_images.py <sim.json> <out_dir>
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/fukushimatakumi/develop")

from PIL import Image, ImageDraw

from slides import _font, FG
from thumb_text import fit_lines

W, H = 1024, 640
ROOT = Path(__file__).resolve().parent.parent
GOLD = (212, 165, 68)


def overlay(src, dst, tag, name):
    im = Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)
    grad = Image.new("L", (1, H))
    for y in range(H):
        t = max(0.0, (y - H * 0.45) / (H * 0.55))
        grad.putpixel((0, y), int(232 * (t ** 1.25)))
    im.paste(Image.new("RGB", (W, H), (5, 8, 14)), (0, 0), grad.resize((W, H)))
    d = ImageDraw.Draw(im)
    d.text((52, H - 180), tag, font=_font("sans_bold", 30), fill=GOLD)
    f, lines, lh = fit_lines(d, lambda s: _font("sans_bold", s), name,
                             W - 104, 130, max_lines=2, hi=72, lo=36)
    y = H - 136
    for ln in lines:
        d.text((52, y), ln, font=f, fill=FG)
        y += lh
    im.save(dst, quality=92)


def main(sim_json, out_dir):
    q = json.loads(Path(sim_json).read_text())
    out = Path(out_dir)
    (out / "img").mkdir(parents=True, exist_ok=True)
    raw = out / "_raw"
    raw.mkdir(exist_ok=True)

    scenes = [{"kind": "image", "prompt": e["image_prompt"]}
              for e in q["endings"].values()]
    tmp = out / "_imgspec.json"
    tmp.write_text(json.dumps({"title": q["title"], "scenes": scenes},
                              ensure_ascii=False))
    print(f"SDXL で {len(scenes)} 枚（約{len(scenes)*2.5:.0f}分）", flush=True)
    subprocess.run(["/Users/fukushimatakumi/develop/music-llm/.venv/bin/python",
                    str(ROOT / "lib/gen_images.py"), str(tmp.resolve()), str(raw.resolve())],
                   check=True, cwd=ROOT)

    pngs = sorted((raw / "imgs").glob("*.png"))
    for (key, e), p in zip(q["endings"].items(), pngs):
        dst = out / "img" / f"{key}.jpg"
        overlay(p, dst, e.get("tag", "ENDING"), e["name"])
        e["image"] = f"img/{key}.jpg"
        print(f"  {key} {e['name']}", flush=True)
    Path(sim_json).write_text(json.dumps(q, ensure_ascii=False, indent=2))
    print(f"SIM_IMG_OK {len(pngs)}枚")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
