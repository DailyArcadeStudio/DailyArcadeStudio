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



# --- 日本語版 ---
# VIDEO_LANG=ja のとき、プレイヤーに見える文字を日本語で作らせる。
# ゲームのロジックとコードは英語のまま（変数名・関数名は触らない）。
import os as _os
_JA = _os.environ.get("VIDEO_LANG", "").lower().startswith("ja")

JA_UI_RULE = """

**画面に出る文字はすべて日本語にしてください。**（日本人向けのチャンネルです）
日本語にするもの:
  - <title> タグ、タイトル画面のゲーム名と説明文
  - START ボタン、操作説明（「スペース / ↓ : ブレーキ」など）
  - HUD の見出し、イベントのバナー、スコアの表示
  - ゲームオーバーの文字（「K.O.」はそのままでよい）、最終スコアの見出し
  - 「もう一度」（Tap to retry / Space to retry にあたるもの）
  - ルール説明パネル（? ボタン）の見出しと本文
  - 戻るリンクは `‹ ゲーム一覧`、ボタンの title 属性も日本語
  - showcase のキャプション（?showcase= で出る被写体の名前）
英語のまま残すもの:
  - 変数名・関数名・window.__ev などのAPI名（ツールが読むので変えない）
  - `?auto=1` などのURLパラメータ名
  - `window.__subjects` / `window.__events` の**中身の識別子**
    （録画ツールが名前で参照するため。画面に出すキャプションだけ日本語にする）
日本語は半角英数より幅を取ります。`clamp()` の値と改行位置に注意して、
小さい画面でもはみ出さないようにしてください。
"""


VARIETY_RULE = """

**操作の型を前作と変えてください（重要）。**
直近に作ったゲームはこれです:
{recent}

上のどれかと同じ操作（同じ指の動き、同じ判断）になっていたら、
別の型にしてください。たとえば:
  - 避けて進む / 速度や間隔を保つ / 積んでバランスを取る
  - タイミングよく押す / 狙って当てる / 選んで振り分ける
  - 覚えて思い出す / 組み立ててつなぐ / 力加減を調整する
「操作が1〜2種類で説明が要らない」ことは保ったまま、
指の動きそのものが違うものにしてください。
絵面（乗り物、動物、走る）が似ていても、操作が違えば別のゲームになります。
"""


def _recent_games(n=4):
    """直近に作ったゲームの名前と中身を返す。プロンプトに埋めて重複を避ける。"""
    out = []
    for g in sorted(GAMES.glob("*/scenes.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True)[:n]:
        try:
            import json
            d = json.loads(g.read_text())
            out.append(f"  - {d.get('title', g.parent.name)}: "
                       f"{(d.get('lead') or d.get('video_title') or '')[:48]}")
        except Exception:
            out.append(f"  - {g.parent.name}")
    return "\n".join(out) or "  （まだありません）"

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
- `window.__subjects` = an array of every valid `?showcase=` name, and
  `window.__events` = an array of every valid `__ev()` name. The recording
  and verification tooling reads these; it cannot guess the names.
- Named events that fire on a shuffled queue, each slamming a banner
  into frame, plus a game-over sequence with slow motion, a camera push
  in, a red flash and a large K.O. with the final score.
- A visible score that increases while alive.
- A **`‹ All games` link back to the gallery** at `../../`, top-left,
  matching the reference's styling. Players arrive on one game from a
  video description and need a route to the others.
- **Sound, synthesised with WebAudio — never an audio file.** Copy the
  SND block from {ref} verbatim and wire it up: a short looping bass
  line that speeds up with the game (`SND.setPace`), a blip per input,
  a stinger on each event, and a hit plus descending motif on the game
  over (`SND.duck`). Add the same mute button (also bound to `M`).
  **Every automated mode must be silent**: declare
  `SILENT = (AUTO || !!SHOWCASE_Q || QS.get('mute')==='1') && !REC` and
  guard every SND call with it. Declare the url flags at the TOP of the
  module, before anything reads them.
- **A `?rec=1` audio-capture mode.** Playwright's recording carries no
  audio, so the game records its own: on `rec=1`, keep the sound ON, tap
  a `MediaStreamDestination` off the master bus with a `MediaRecorder`,
  and expose `window.__recStop()` returning the bytes. Copy this from
  {ref} verbatim.
- The `?auto=1` start path MUST go through `startRun()`, not a separate
  inline copy — otherwise sound and recording never start.
- Keep the game's sounds distinct and readable on their own: they are
  mixed under narration in both the main video and the short, so a
  wash of noise is useless. Short, pitched, recognisable events.

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
    if _JA:
        prompt += JA_UI_RULE
    prompt += VARIETY_RULE.format(recent=_recent_games())
    print(f"GENERATING {slug}…", flush=True)
    r = subprocess.run([CLAUDE, "-p", prompt, "--permission-mode", "acceptEdits",
                        "--dangerously-skip-permissions"],
                       cwd=ROOT, capture_output=True, text=True, timeout=3000)
    if r.returncode != 0:
        raise SystemExit(f"claude failed: {r.stderr[-400:]}")
    if not dst.exists():
        raise SystemExit(f"claude produced no file at {dst}")
    return dst


def _lit_pixels(png_bytes):
    """描画されたピクセルの割合。背景はほぼ黒なので、明るい画素を数える。"""
    import io
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB").resize((160, 90))
    px = list(im.getdata())
    lit = sum(1 for r, g, b in px if r + g + b > 150)
    return lit / len(px)


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
          subjects: Array.isArray(window.__subjects) ? window.__subjects : null,
          events: Array.isArray(window.__events) ? window.__events : null,
        })""")
        if not state["alive"]:
            problems.append("autopilot did not start")
        for hook in ("hasEv", "hasKill", "hasShowcase"):
            if not state[hook]:
                problems.append(f"missing hook {hook}")
        if not state["subjects"]:
            problems.append("window.__subjects not declared")
        if not state["events"]:
            problems.append("window.__events not declared")
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

        # Every declared subject must actually render. Subject names differ
        # per game (ninja / lantern / ...), so read them from the game
        # rather than assuming one.
        for subj in (state["subjects"] or [])[:8]:
            pg.goto(f"{base}?showcase={subj}&sx=1&nolabel=1")
            pg.wait_for_timeout(2200)
            # Count lit pixels rather than trusting the PNG size: a wide flat
            # subject (a bridge) fills little of a 16:9 frame and compresses
            # small, which read as "empty" even though it rendered fine.
            # The canvas cannot be read from JS (preserveDrawingBuffer is off),
            # so measure the screenshot instead.
            lit = _lit_pixels(pg.screenshot())
            if lit < 0.004:                   # 0.4% of the frame
                problems.append(f"showcase '{subj}' looks empty ({lit:.3%})")

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
