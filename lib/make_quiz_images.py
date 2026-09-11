"""診断の結果画像を作る。

SDXL は文字を正しく描けないので、**絵だけ**を生成させ、
タイプ名などの文字は PIL で後から重ねる（サムネ生成と同じ考え方）。

    python make_quiz_images.py <quiz.json> <out_dir>

quiz.json の results[key] に image_prompt があり、そこから1枚ずつ作る。
16タイプで SDXL 約40分。
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/Users/fukushimatakumi/develop")

from PIL import Image, ImageDraw, ImageFilter

from slides import _font, FG, YELLOW
from thumb_text import fit_lines

W, H = 1024, 1024        # 正方形。診断ページでは幅いっぱいに出る
ROOT = Path(__file__).resolve().parent.parent


def overlay(src, dst, type_key, name):
    """絵に「タイプ記号 + 名前」を重ねる。画像自体に文字は入っていない前提。"""
    im = Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)

    # 下半分を暗くして文字を読ませる（写真をつぶしすぎない）
    grad = Image.new("L", (1, H))
    for y in range(H):
        t = max(0.0, (y - H * 0.52) / (H * 0.48))
        grad.putpixel((0, y), int(225 * (t ** 1.3)))
    mask = grad.resize((W, H))
    im.paste(Image.new("RGB", (W, H), (6, 9, 15)), (0, 0), mask)

    d = ImageDraw.Draw(im)
    # タイプ記号（小さく、上に）
    ft = _font("sans_bold", 40)
    d.text((60, H - 300), type_key, font=ft, fill=YELLOW)
    # 名前（大きく、折り返しあり）
    f, lines, lh = fit_lines(d, lambda s: _font("sans_bold", s), name,
                             W - 120, 200, max_lines=2, hi=92, lo=40)
    y = H - 240
    for ln in lines:
        d.text((60, y), ln, font=f, fill=FG)
        y += lh
    im.save(dst, quality=92)
    return dst


def main(quiz_json, out_dir):
    q = json.loads(Path(quiz_json).read_text())
    out = Path(out_dir)
    (out / "img").mkdir(parents=True, exist_ok=True)
    raw = out / "_raw"
    raw.mkdir(exist_ok=True)

    # SDXL に渡す用の一時 problem.json（既存の gen_images.py を使い回す）
    scenes = [{"kind": "image", "prompt": r["image_prompt"]}
              for r in q["results"].values()]
    tmp = out / "_imgspec.json"
    tmp.write_text(json.dumps({"title": q["title"], "scenes": scenes},
                              ensure_ascii=False))
    print(f"SDXL で {len(scenes)} 枚（約{len(scenes)*2.5:.0f}分）", flush=True)
    subprocess.run(["/Users/fukushimatakumi/develop/music-llm/.venv/bin/python",
                    str(ROOT / "lib/gen_images.py"), str(tmp.resolve()), str(raw.resolve())],
                   check=True, cwd=ROOT)

    # 生成された 00.png, 01.png ... を results の順に割り当てて文字を重ねる
    pngs = sorted((raw / "imgs").glob("*.png"))
    for (key, r), p in zip(q["results"].items(), pngs):
        dst = out / "img" / f"{key}.jpg"
        overlay(p, dst, key, r["name"])
        r["image"] = f"img/{key}.jpg"
        print(f"  {key} {r['name']}", flush=True)

    # image のパスを書き戻す
    Path(quiz_json).write_text(json.dumps(q, ensure_ascii=False, indent=2))
    print(f"QUIZ_IMG_OK {len(pngs)}枚")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
