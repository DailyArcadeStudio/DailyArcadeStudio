"""Build one full episode for a game: record, narrate, assemble, short.

Resumable — every step is skipped if its artifact already exists, so a
run that dies partway can be re-run without redoing the slow parts.

usage: python lib/make_episode.py <slug> [work_dir]
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = Path("/Users/fukushimatakumi/develop/music-llm")
PY = str(ML / ".venv/bin/python")
PY_K = str(ML / ".venv-kokoro/bin/python")
PORT = 8901


def log(m):
    print(f"[episode] {m}", flush=True)


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def serve():
    srv = subprocess.Popen(["python3", "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    return srv


def main(slug, work_dir=None):
    scenes = ROOT / "games" / slug / "scenes.json"
    if not scenes.exists():
        raise SystemExit(f"no scenes.json for {slug} — write the storyboard first")
    work = Path(work_dir or f"/tmp/ep_{slug}")
    work.mkdir(parents=True, exist_ok=True)
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    env = {**os.environ, "GAME_SLUG": slug, "EP_WORK": str(work)}

    srv = serve()
    try:
        # 1. gameplay: the staged run, plus a calm bed for the narration
        if not (work / "raw.mp4").exists():
            log("recording gameplay")
            run([PY, str(ROOT / "lib/capture.py"), slug, str(work)], env=env)
        else:
            log("gameplay already recorded")

        # 2. story images (slow: SDXL). Skipped when the scenes need none.
        if not (work / "imgs").exists():
            log("generating story images")
            run([PY, str(ROOT / "lib/gen_images.py"), str(scenes), str(work)])

        # 3. narration
        if not (work / "narration.wav").exists():
            log("narrating")
            run([PY_K, str(ROOT / "lib/narrate.py"), str(scenes), str(work)])

        # 4. main video
        main_mp4 = out / f"{slug}.mp4"
        log("assembling main video")
        run([PY, str(ROOT / "lib/assemble.py"), str(scenes), str(work), str(main_mp4)],
            env=env)

        # 5. vertical short
        short_mp4 = out / f"short_{slug}.mp4"
        log("building short")
        run([PY, str(ROOT / "lib/make_short.py"), str(work), str(short_mp4)], env=env)
    finally:
        srv.terminate()

    print(json.dumps({"main": str(main_mp4), "short": str(short_mp4)}))
    log(f"EPISODE_OK {slug}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
