"""Generate one playable game with the claude CLI, then verify it runs.

A game is only accepted if a real browser can load it, start the
autopilot, score points, and expose the recording hooks. A game that
fails verification is left in place but not marked built, so the next
run retries it rather than shipping a broken page.

usage: python lib/make_game.py <slug> "<title>" "<idea>"
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAMES = ROOT / "games"
CLAUDE = "/opt/homebrew/bin/claude"
REFERENCE = GAMES / "ninja-dash" / "index.html"

PROMPT = """Build a browser game: {title}

Concept: {idea}

Write ONE file: {dst}

Study {ref} first and copy its structure exactly. It is the reference
implementation for this channel. In particular you MUST reproduce:

- A single self-contained HTML file. Three.js from the CDN via importmap
  (https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js).
  No build step, no external assets, no image or audio files.
- A title screen with a START button, and keyboard controls.
- **It MUST be playable on a phone.** Most players arrive from a phone,
  so touch is not optional:
  - swipe / tap on the canvas for every action a key can do
  - the START button and the title overlay must both respond to
    `touchend`, not only `click` (click alone is unreliable on touch)
  - after a game over, show "Tap to retry" on touch devices
    (`matchMedia('(pointer:coarse)')`) and let a tap restart
  - `preventDefault` on `touchmove` so the page does not scroll or zoom
  - route keyboard and touch through the SAME action functions, so the
    two input paths cannot drift apart
- **It MUST work in portrait AND landscape.** A phone held upright is far
  narrower than 16:9, so a fixed FOV pushes the playfield out of frame:
  widen the camera's vertical FOV as the aspect ratio gets taller, and
  re-fit on both `resize` and `orientationchange`. Size the HUD, title
  and game-over text with `clamp()` so nothing overflows a small screen.
- `?auto=1` autopilot that plays the game competently on its own.
- `?hold=<ms>` to control the delay before an auto-retry.
- `?noev=1` to suppress the random events (used to record calm footage).
- `?showcase=<subject>` which hides the game and puts ONE object on a
  turntable against an empty stage, with the camera fitted to the
  object's bounding box. `?sx=1` biases the subject left, `?nolabel=1`
  hides the caption. Subjects must cover the player and every hazard.
- window.__ev(name), window.__kill(), window.__alive(), window.__showcase(name).
  __ev must return false when the run is already over.
- Named events that fire on a shuffled queue, each slamming a banner
  into frame, plus a game-over sequence with slow motion, a camera push
  in, a red flash and a large K.O. with the final score.
- A visible score that increases while alive.

Keep it readable and comment the parts that are not obvious. Match the
reference's visual language: dark background, a strong accent colour,
primitive shapes only (no models). Make the events genuinely different
from each other so the footage has variety.

Write only that one file, then stop."""


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def generate(slug, title, idea):
    dst = GAMES / slug / "index.html"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        print(f"EXISTS {dst}", flush=True)
        return dst
    prompt = PROMPT.format(title=title, idea=idea, dst=dst, ref=REFERENCE)
    print(f"GENERATING {slug}…", flush=True)
    r = subprocess.run([CLAUDE, "-p", prompt, "--permission-mode", "acceptEdits",
                        "--dangerously-skip-permissions"],
                       cwd=ROOT, capture_output=True, text=True, timeout=3000)
    if r.returncode != 0:
        raise SystemExit(f"claude failed: {r.stderr[-400:]}")
    if not dst.exists():
        raise SystemExit(f"claude produced no file at {dst}")
    return dst


def verify(slug, port=8901):
    """Load the game in a real browser and confirm it is actually playable."""
    from playwright.sync_api import sync_playwright
    base = f"http://localhost:{port}/games/{slug}/index.html"
    problems = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        pg.goto(base + "?auto=1")
        pg.wait_for_timeout(6000)
        state = pg.evaluate("""()=>({
          alive: !!(window.__alive && window.__alive()),
          hasEv: typeof window.__ev === 'function',
          hasKill: typeof window.__kill === 'function',
          hasShowcase: typeof window.__showcase === 'function',
          score: (document.querySelector('#score')||{}).textContent || '',
        })""")
        if not state["alive"]:
            problems.append("autopilot did not start")
        for hook in ("hasEv", "hasKill", "hasShowcase"):
            if not state[hook]:
                problems.append(f"missing hook {hook}")
        try:
            if int("".join(c for c in state["score"] if c.isdigit()) or 0) <= 0:
                problems.append("score never increased")
        except ValueError:
            problems.append(f"unreadable score {state['score']!r}")

        # a phone must be able to play it: tap to start, then score
        pg.goto(base)
        pg.wait_for_timeout(1200)
        mob = pg.context.browser.new_context(
            viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        mp = mob.new_page()
        mp.goto(base)
        mp.wait_for_timeout(1500)
        mp.touchscreen.tap(195, 675)          # START button area
        mp.wait_for_timeout(4000)
        sc = mp.evaluate("()=>(document.querySelector('#score')||{}).textContent||''")
        if int("".join(c for c in sc if c.isdigit()) or 0) <= 0:
            problems.append("not playable in portrait on touch")
        mob.close()

        # the showcase stage must render something, not a blank frame
        pg.goto(base + "?showcase=player&sx=1&nolabel=1")
        pg.wait_for_timeout(2500)
        shot = pg.screenshot()
        if len(shot) < 12000:                 # a blank dark frame compresses tiny
            problems.append("showcase looks empty")

        if errs:
            problems.append(f"js errors: {errs[:2]}")
        b.close()
    return problems


def main(slug, title, idea):
    generate(slug, title, idea)
    srv = subprocess.Popen(["python3", "-m", "http.server", "8901"], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    try:
        problems = verify(slug)
    finally:
        srv.terminate()
    if problems:
        print("VERIFY_FAILED " + "; ".join(problems), flush=True)
        raise SystemExit(1)
    print(f"GAME_OK games/{slug}/index.html", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
