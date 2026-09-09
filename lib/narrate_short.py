"""ショートの各ビートのナレーションを Kokoro で作る。

`scenes.json` の "short" の headline をそのまま読ませ、
<work>/short_narr/<i>.wav と durations.json を書く。
make_short.py がそれを各ビートに乗せる。

MUST run under .venv-kokoro.
usage: python lib/narrate_short.py <slug> <work_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

ROOT = Path(__file__).resolve().parent.parent
SR = 24000
PAD = 0.35          # 読み終わりの余韻


def main(slug, work_dir):
    scenes = json.loads((ROOT / "games" / slug / "scenes.json").read_text())
    # short_v2.cuts の narration を読む（旧 short[].headline にも対応）
    cuts = (scenes.get("short_v2") or {}).get("cuts")
    beats = ([{"headline": c.get("narration", "")} for c in cuts] if cuts
             else scenes.get("short") or [])
    beats = [b for b in beats] if beats else []
    if not beats:
        print("NO_SHORT_BEATS"); return
    voice = scenes.get("voice", "am_adam")
    out = Path(work_dir) / "short_narr"
    out.mkdir(parents=True, exist_ok=True)

    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    durs = []
    for i, b in enumerate(beats):
        text = b.get("headline", "")
        if not text.strip():                 # 無言のカットは無音ファイルを置く
            sf.write(out / f"{i}.wav", np.zeros(int(SR*0.2), dtype=np.float32), SR)
            durs.append(0.0); print(f"  cut{i}  (無言)", flush=True); continue
        chunks = [a for _g, _p, a in pipe(text, voice=voice)]
        audio = (np.concatenate(chunks).astype(np.float32) if chunks
                 else np.zeros(int(SR * 0.3), dtype=np.float32))
        audio = np.concatenate([audio, np.zeros(int(SR * PAD), dtype=np.float32)])
        sf.write(out / f"{i}.wav", audio, SR)
        durs.append(round(len(audio) / SR, 3))
        print(f"  beat{i} {durs[-1]:4.1f}s  {text}", flush=True)

    (out / "durations.json").write_text(json.dumps(durs))
    print(f"SHORT_NARR_OK {sum(durs):.1f}s total")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
