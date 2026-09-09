"""縦ショート(1080x1920)を作る。

ショートは本編の要約ではなく**入口**。構成は固定:

  1. フック    一番派手なプレイ映像 +「今日のゲーム」
  2. 紹介      showcase(中央撮り)でキャラ/主役を見せる
  3. 仕組み    showcaseでハザードを見せ、一言だけ添える
  4. プレイ    イベント〜K.O.をまとめて見せる
  5. 誘導      「概要欄のリンクから遊べる」

オチ（何秒もつか等）は本編に取っておく。

usage: python lib/make_short.py <work_dir> <out.mp4>
env:   GAME_SLUG, GAME_TITLE
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from slides import _font, _wrap, FG, YELLOW, ACCENT

ROOT = Path(__file__).resolve().parent.parent
SW, SH = 1080, 1920
FPS = 30
# 4:3 に切って大きく見せる。動きは画面中央にあるので端は捨てて良い。
VID_W, VID_H = SW, 810
VID_TOP = 940 - VID_H // 2
GAME_VOL = 0.5      # ゲーム音はナレーションの下に敷く


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                        str(path)], capture_output=True, text=True)
    return "audio" in r.stdout


def band(headline, dst, title, cta=None):
    """上に見出し、下にゲーム名。cta があれば下段を誘導文に差し替える。"""
    img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, SW, VID_TOP), fill=(8, 11, 17, 255))
    d.rectangle((0, VID_TOP + VID_H, SW, SH), fill=(8, 11, 17, 255))

    if headline:
        f = _font("sans_bold", 76)
        lines = _wrap(d, headline, f, SW - 120)
        y = VID_TOP - 40 - len(lines) * 92
        for ln in lines:
            w = d.textlength(ln, font=f)
            d.text(((SW - w) / 2, y), ln, font=f, fill=YELLOW + (255,))
            y += 92

    # 見出しがゲーム名そのものなら、下段の名前は省く（同じ語が2つ並ぶ）
    show_title = (headline or "").strip().upper() != title.strip().upper()
    if show_title:
        fn = _font("sans_bold", 78)
        w = d.textlength(title, font=fn)
        d.text(((SW - w) / 2, VID_TOP + VID_H + 60), title, font=fn, fill=FG + (255,))
    sub = cta or "link in the description"
    fs = _font("sans_bold" if cta else "sans", 46 if cta else 42)
    w = d.textlength(sub, font=fs)
    d.text(((SW - w) / 2, VID_TOP + VID_H + (165 if show_title else 90)),
           sub, font=fs, fill=(YELLOW if cta else ACCENT) + (255,))
    img.save(dst)


def seg(src, start, dur, overlay, wav, dst, zoom=1.0, game_audio=False):
    """1カット作る。src は動画（プレイ/showcase）。

    zoom>1 は showcase 用。被写体は 16:9 の中央に小さく写っているので、
    4:3 に切るだけだとさらに小さくなる。
    """
    sw, sh = int(VID_W * zoom), int(VID_H * zoom)
    fit = (f"[0:v]scale={sw}:{sh}:force_original_aspect_ratio=increase,"
           f"crop={VID_W}:{VID_H}[vid];" if zoom != 1.0 else
           f"[0:v]scale={VID_W}:{VID_H}:force_original_aspect_ratio=increase,"
           f"crop={VID_W}:{VID_H}[vid];")
    fc = (f"color=c=black:s={SW}x{SH}:r={FPS}[base];" + fit +
          f"[base][vid]overlay=0:{VID_TOP}[tmp];"
          f"[tmp][1:v]overlay=0:0[v]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-ss", f"{max(start, 0):.3f}", "-i", str(src),
           "-loop", "1", "-i", str(overlay)]
    has_narr = bool(wav and Path(wav).exists())
    if has_narr and game_audio:
        # ナレーションを前に、ゲーム音を下に敷く（ナレが埋もれない音量）
        cmd += ["-i", str(wav),
                "-filter_complex",
                fc + ";[2:a]apad,volume=1.0[nar];"
                     f"[0:a]volume={GAME_VOL}[gm];"
                     "[nar][gm]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    elif game_audio:
        cmd += ["-filter_complex", fc + f";[0:a]volume={GAME_VOL}[a]",
                "-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    elif has_narr:
        cmd += ["-i", str(wav),
                "-filter_complex", fc + ";[2:a]apad[a]",
                "-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    else:
        cmd += ["-filter_complex", fc, "-map", "[v]", "-an"]
    cmd += ["-t", f"{dur:.3f}", "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(dst)]
    run(cmd)


def main(work_dir, out_path):
    work = Path(work_dir)
    tmp = work / "short"
    tmp.mkdir(parents=True, exist_ok=True)
    slug = os.environ.get("GAME_SLUG", "")
    title = os.environ.get("GAME_TITLE", "GAME")
    raw = work / "raw.mp4"
    sc_dir = work / "showcase_center"
    marks = {n: t for n, t in json.loads((work / "marks.json").read_text())["marks"]}
    scenes = json.loads((ROOT / "games" / slug / "scenes.json").read_text())
    spec = scenes.get("short_v2") or {}
    narr = work / "short_narr"
    durs = []
    if (narr / "durations.json").exists():
        durs = json.loads((narr / "durations.json").read_text())

    cuts = spec.get("cuts") or []
    if not cuts:
        raise SystemExit("scenes.json に short_v2.cuts がありません")

    segs = []
    for i, c in enumerate(cuts):
        ov = tmp / f"band{i}.png"
        band(c.get("headline", ""), ov, title, cta=c.get("cta"))
        wav = narr / f"{i}.wav"
        dur = c.get("dur", 5.0)
        if i < len(durs):
            dur = max(dur, durs[i] + 0.5)   # 読み終わる前に切らない
        dst = tmp / f"seg{i}.mp4"
        if c["kind"] == "showcase":
            src, start, zoom = sc_dir / f"{c['subject']}.mp4", 1.2, 1.55
        else:
            src, start, zoom = raw, marks.get(c["mark"], 2) + c.get("lead", 0), 1.0
        # プレイ映像には録れたゲーム音がある。showcase は無音で撮っている。
        use_game = (c["kind"] != "showcase") and has_audio(src)
        seg(src, start, dur, ov, wav, dst, zoom=zoom, game_audio=use_game)
        segs.append(dst)
        what = c.get("subject") or c.get("mark")
        print(f"  cut{i} {c['kind']:9s} {str(what):10s} {dur:4.1f}s  "
              f"{c.get('headline') or c.get('cta','')}", flush=True)

    lst = tmp / "list.txt"
    lst.write_text("\n".join(f"file '{s.resolve()}'" for s in segs))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", str(out_path)])
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1",
                        str(out_path)], capture_output=True, text=True).stdout.strip()
    print(f"SHORT_OK {out_path} {float(d):.1f}s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
