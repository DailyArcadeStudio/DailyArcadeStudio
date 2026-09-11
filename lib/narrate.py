"""Kokoro narration for the Ninja Dash video.

Writes narration.wav plus timing.json (one {start,dur} per scene) so
assemble.py can hold each slide/clip exactly as long as its line.

MUST run under .venv-kokoro.
usage: python lib/narrate.py scenes.json out_dir
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
try:
    from kokoro import KPipeline
except Exception:
    KPipeline = None


# --- 日本語(VOICEVOX)対応 ---
# VIDEO_LANG=ja のとき Kokoro ではなく VOICEVOX(四国めたん)で合成する。
import os as _os, sys as _sys
_sys.path.insert(0, "/Users/fukushimatakumi/develop")
_JA = _os.environ.get("VIDEO_LANG", "").lower().startswith("ja")
if _JA:
    from vv_tts import ensure_engine as _vv_ensure, synth as _vv_synth
    _vv_ensure()

SR = 24000
GAP = 0.45          # silence between scenes


def synth(pipe, text, voice):
    if _JA:
        return _vv_synth(text)[0]
    chunks = [a for _gs, _ps, a in pipe(text, voice=voice)]
    if not chunks:
        return np.zeros(int(SR * 0.3), dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32)


def main(scenes_path, out_dir):
    data = json.loads(Path(scenes_path).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    voice = data.get("voice", "am_adam")

    pipe = None if _JA else KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    gap = np.zeros(int(SR * GAP), dtype=np.float32)

    parts, timing, cursor = [], [], 0.0
    for sc in data["scenes"]:
        audio = synth(pipe, sc["narration"], voice)
        dur = len(audio) / SR
        timing.append({"kind": sc["kind"], "clip": sc.get("clip"),
                       "start": round(cursor, 3), "dur": round(dur, 3)})
        parts.append(audio)
        parts.append(gap)
        cursor += dur + GAP

    sf.write(out / "narration.wav", np.concatenate(parts), SR)
    (out / "timing.json").write_text(json.dumps(timing, indent=2))
    print(f"NARR_OK {cursor:.1f} sec, {len(timing)} scenes")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
