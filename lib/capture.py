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


def to_mp4(webm, dst, audio=None):
    """webm -> mp4。audio があればゲーム音として乗せる。"""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm)]
    if audio and Path(audio).exists():
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a",
                "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "30", str(dst)]
    subprocess.run(cmd, check=True)


def newest(d):
    # audio.webm はこちらで書いた音声なので、映像として拾わない
    v = [f for f in sorted(glob.glob(str(Path(d) / "*.webm")), key=os.path.getmtime)
         if Path(f).name != "audio.webm"]
    if not v:
        raise SystemExit(f"no recording produced in {d}")
    return v[-1]


def record(url, seconds, out_dir, drive=None, want_audio=False):
    """Record one page; `drive` may script the page while it records.

    Playwright の録画には音声が入らない。want_audio のときは URL に
    rec=1 を付け、ゲーム自身に WebAudio の master を録らせて .webm を
    別に書き出す（鳴っているものそのものなので映像と同期する）。
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    audio_bytes = None
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--enable-unsafe-swiftshader",
                                    "--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport=VIEW, record_video_dir=str(out_dir),
                            record_video_size=VIEW)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        if want_audio:
            url += ("&" if "?" in url else "?") + "rec=1"
        pg.goto(url)
        result = drive(pg) if drive else pg.wait_for_timeout(seconds * 1000)
        if want_audio:
            try:
                audio_bytes = pg.evaluate("()=>window.__recStop()")
            except Exception as e:
                log(f"WARNING 音声取得に失敗: {e}")
        ctx.close()
        b.close()
    if errs:
        log(f"WARNING page errors: {errs[:2]}")
    if audio_bytes:
        Path(out_dir, "audio.webm").write_bytes(bytes(audio_bytes))
        log(f"  game audio: {len(audio_bytes)//1024} KB")
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

    webm, _ = record(base + "?auto=1&hold=11000", None, work / "_raw", drive,
                     want_audio=True)
    to_mp4(webm, work / "raw.mp4", audio=work / "_raw" / "audio.webm")
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

    # 本編用（左寄せ：右にテキストを置く）
    sc = work / "showcase"
    sc.mkdir(exist_ok=True)
    for s in subjects:
        webm, _ = record(f"{base}?showcase={s}&sx=1&nolabel=1", 20, sc / f"_{s}")
        to_mp4(webm, sc / f"{s}.mp4")
        log(f"showcase/{s}.mp4")

    # 縦ショート用（中央：縦画面は横に余白がない）
    scc = work / "showcase_center"
    scc.mkdir(exist_ok=True)
    for s in subjects:
        webm, _ = record(f"{base}?showcase={s}&nolabel=1", 10, scc / f"_{s}")
        to_mp4(webm, scc / f"{s}.mp4")
        log(f"showcase_center/{s}.mp4")
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
    else:
        # no storyboard yet: fall back to what the game itself declares
        from playwright.sync_api import sync_playwright as _sp
        with _sp() as _p:
            _b = _p.chromium.launch(args=["--enable-unsafe-swiftshader"])
            _pg = _b.new_page()
            _pg.goto(f"http://localhost:{PORT}/games/{slug}/index.html")
            _pg.wait_for_timeout(1500)
            EVENTS = _pg.evaluate("()=>window.__events") or EVENTS
            SUBJECTS = _pg.evaluate("()=>window.__subjects") or SUBJECTS
            _b.close()
    main(slug, work, SUBJECTS)
