"""Record the footage an episode needs.

Writes into <work>:
  raw.mp4        staged run — every event fired on cue, then a death
  marks.json     when each beat happens inside raw.mp4
  bed.mp4        a long event-free run, to sit behind narration
  showcase/*.mp4 one turntable clip per subject

Events are only fired at a live run: firing one onto the K.O. screen
produces a banner over a death, which is unusable footage.

usage: python lib/capture.py <slug> <work_dir> [subjects...]
"""
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8901
VIEW = {"width": 1280, "height": 720}


def log(m):
    print(f"[capture] {m}", flush=True)


def to_mp4(webm, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-r", "30", str(dst)], check=True)


def newest(d):
    v = sorted(glob.glob(str(Path(d) / "*.webm")), key=os.path.getmtime)
    if not v:
        raise SystemExit(f"no recording produced in {d}")
    return v[-1]


def record(url, seconds, out_dir, drive=None):
    """Record one page; `drive` may script the page while it records."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
        ctx = b.new_context(viewport=VIEW, record_video_dir=str(out_dir),
                            record_video_size=VIEW)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(url)
        result = drive(pg) if drive else pg.wait_for_timeout(seconds * 1000)
        ctx.close()
        b.close()
    if errs:
        log(f"WARNING page errors: {errs[:2]}")
    return newest(out_dir), result


def staged_run(base, work):
    """The main recording: each event fired on cue, then a staged death."""
    marks = []

    def drive(pg):
        t0 = time.time()

        def mark(label):
            marks.append((label, round(time.time() - t0, 2)))

        def alive():
            return pg.evaluate("()=>window.__alive && window.__alive()")

        def wait_alive(timeout_ms=25000):
            waited = 0
            while not alive() and waited < timeout_ms:
                pg.wait_for_timeout(250)
                waited += 250

        def fire(name):
            # only into a live run — a banner over a K.O. is unusable
            for _ in range(100):
                if alive() and pg.evaluate(f"()=>window.__ev('{name}')"):
                    mark(name)
                    return True
                pg.wait_for_timeout(250)
            log(f"WARNING could not fire {name}")
            return False

        mark("title")
        pg.wait_for_timeout(1400)
        wait_alive()
        mark("run_start")
        pg.wait_for_timeout(5000)

        for name in EVENTS:
            fire(name)
            pg.wait_for_timeout(7000)

        wait_alive()
        pg.wait_for_timeout(2500)
        mark("pre_death")
        pg.evaluate("()=>window.__kill()")
        mark("death")
        pg.wait_for_timeout(9500)
        wait_alive()
        mark("run2")
        pg.wait_for_timeout(7000)

    webm, _ = record(base + "?auto=1&hold=11000", None, work / "_raw", drive)
    to_mp4(webm, work / "raw.mp4")
    (work / "marks.json").write_text(json.dumps({"marks": marks}, indent=2))
    log(f"raw.mp4 + {len(marks)} marks")


def main(slug, work_dir, subjects=None):
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)
    base = f"http://localhost:{PORT}/games/{slug}/index.html"
    subjects = subjects or SUBJECTS

    staged_run(base, work)

    # a long calm run for narration beds — no events, no deaths
    webm, _ = record(base + "?auto=1&noev=1", 75, work / "_bed")
    to_mp4(webm, work / "bed.mp4")
    log("bed.mp4")

    sc = work / "showcase"
    sc.mkdir(exist_ok=True)
    for s in subjects:
        webm, _ = record(f"{base}?showcase={s}&sx=1&nolabel=1", 20, sc / f"_{s}")
        to_mp4(webm, sc / f"{s}.mp4")
        log(f"showcase/{s}.mp4")
    log("CAPTURE_OK")


# Per-game event and subject names, read from the game's scenes.json when
# present so a new game does not need this file edited.
EVENTS = ["surge", "wall", "blackout", "boss"]
SUBJECTS = ["ninja", "shuriken", "rock", "wall", "boss"]

if __name__ == "__main__":
    slug = sys.argv[1]
    work = sys.argv[2]
    scenes = ROOT / "games" / slug / "scenes.json"
    if scenes.exists():
        data = json.loads(scenes.read_text())
        EVENTS = data.get("events", EVENTS)
        subs = [s["subject"] for s in data["scenes"] if s.get("subject")]
        SUBJECTS = subs or SUBJECTS
    main(slug, work, SUBJECTS)
