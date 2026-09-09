"""Assemble the Ninja Dash video.

Scene kinds:
  hook / events / death  gameplay cut from the screen recording
  image                  SDXL still + lower-third caption (the story beats)
  showcase               turntable clip of one game object + a text panel
  outro                  full-frame card

Every segment is held to its own narration line, crossfaded, then the
narration is muxed on.

usage: python lib/assemble.py scenes.json work_dir out.mp4
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overlays

FPS = 30
W, H = 1920, 1080
XFADE = 0.4

# All footage lives in the work dir, written by lib/capture.py.
def _paths(work):
    return {"raw": work / "raw.mp4", "marks": work / "marks.json",
            "showcase": work / "showcase",
            # long event-free run, recorded with ?noev=1
            "bed": work / "bed.mp4"}

# Lead-in per clip kind. Event names differ per game (boss / quake / ...),
# so anything not named here falls back to a small lead: an event clip
# should open on its banner, not a second before it.
CLIP_LEAD = {
    "run":    ("run_start", 0.8),    # clean running, no events yet
    "death":  ("death", -2.2),       # lead in before the hit, then K.O.
}
DEFAULT_EVENT_LEAD = -0.2


def clip_source(clip, marks, events):
    """(mark, lead) for a clip name, whatever the game calls its events."""
    if clip in CLIP_LEAD:
        return CLIP_LEAD[clip]
    if clip == "events":
        # "events" means the montage: start at the first event that was fired
        first = next((e for e in events if e in marks), None)
        return (first or "run_start"), -0.6
    if clip in marks:                # a named event of this game
        return clip, DEFAULT_EVENT_LEAD
    # unknown: fall back to clean running rather than crashing the build
    print(f"  WARN clip '{clip}' has no mark; using run_start", flush=True)
    return "run_start", 0.8

# Where in the calm bed each story beat starts. The bed has no events and
# no deaths, so nothing under the narration pulls the eye off the story.
STORY_BED_AT = [2.0, 14.0, 28.0, 45.0]


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def marks_map(marks_path):
    return {name: t for name, t in json.loads(Path(marks_path).read_text())["marks"]}


GAME_VOL = 0.34     # ナレーションの下に敷く音量（本編はナレが主役）


def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                        str(path)], capture_output=True, text=True)
    return "audio" in r.stdout


def game_audio_track(cuts, total, work, dst):
    """プレイカットのゲーム音だけを並べた1本のトラックを作る。

    本編は全セグメントを無音で作ってから最後にナレーションを乗せる構造。
    プレイ部分にだけゲーム音を入れたいので、各カットの音声を
    タイムライン上の位置に遅延させて重ねた別トラックを作り、
    最後にナレーションとミックスする。
    """
    if not cuts:
        return None
    inputs, filters, labels = [], [], []
    for n, (src, start, dur, at) in enumerate(cuts):
        inputs += ["-ss", f"{max(start,0):.3f}", "-t", f"{dur:.3f}", "-i", str(src)]
        filters.append(f"[{n}:a]adelay={int(at*1000)}|{int(at*1000)},"
                       f"volume={GAME_VOL}[g{n}]")
        labels.append(f"[g{n}]")
    mix = (f"{''.join(labels)}amix=inputs={len(labels)}:"
           f"duration=longest:dropout_transition=0,apad[out]")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(filters + [mix]),
         "-map", "[out]", "-t", f"{total:.3f}",
         "-c:a", "aac", "-b:a", "160k", str(dst)])
    return dst


def _encode(extra, dst):
    run(["ffmpeg", "-y", "-loglevel", "error", *extra, "-r", str(FPS),
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-an", str(dst)])


def seg_still(png, dur, dst):
    _encode(["-loop", "1", "-i", str(png), "-t", f"{dur:.3f}",
             "-vf", f"scale={W}:{H}"], dst)


def seg_image(img, overlay_png, dur, dst):
    """SDXL still under a caption overlay, held for the line."""
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    _encode(["-loop", "1", "-i", str(img), "-loop", "1", "-i", str(overlay_png),
             "-filter_complex", f"[0:v]{fit}[bg];[bg][1:v]overlay=0:0[v]",
             "-map", "[v]", "-t", f"{dur:.3f}"], dst)


def seg_clip(src, start, dur, overlay_png, dst, pan=0.0):
    """Cut gameplay/showcase footage, upscale, and lay text over it.

    pan shifts the picture sideways as a fraction of width (negative moves
    the content right), for when an overlay covers one side of frame.
    """
    fit = f"scale={W}:{H}:flags=lanczos"
    if pan:
        # zoom slightly so the shift does not expose an empty edge
        zw, zh = int(W * 1.22), int(H * 1.22)
        off = int(W * pan) + (zw - W) // 2
        fit = (f"scale={zw}:{zh}:flags=lanczos,"
               f"crop={W}:{H}:{max(0, min(zw - W, off))}:{(zh - H) // 2}")
    if overlay_png:
        _encode(["-ss", f"{max(start,0):.3f}", "-i", str(src),
                 "-loop", "1", "-i", str(overlay_png),
                 "-filter_complex", f"[0:v]{fit}[bg];[bg][1:v]overlay=0:0[v]",
                 "-map", "[v]", "-t", f"{dur:.3f}"], dst)
    else:
        _encode(["-ss", f"{max(start,0):.3f}", "-i", str(src),
                 "-t", f"{dur:.3f}", "-vf", fit], dst)


def concat_xfade(segs, work, kinds=None):
    """segs = [(path, dur)]. `kinds` lets same-layout neighbours wipe.

    A plain dissolve between two showcase scenes double-exposes two text
    panels in the same place, which reads as garbled overlap. A wipe
    slides one over the other instead.
    """
    if len(segs) == 1:
        return segs[0][0]
    inputs = []
    for p, _ in segs:
        inputs += ["-i", str(p)]
    fc, prev, cum = [], "0:v", segs[0][1]
    for i in range(1, len(segs)):
        out = f"v{i}"
        same = (kinds and i < len(kinds)
                and kinds[i] == kinds[i-1] == "showcase")
        trans = "wipeleft" if same else "fade"
        fc.append(f"[{prev}][{i}:v]xfade=transition={trans}:"
                  f"duration={XFADE}:offset={cum - XFADE:.3f}[{out}]")
        prev = out
        cum = cum - XFADE + segs[i][1]
    final = work / "video_novoice.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
         "-filter_complex", ";".join(fc), "-map", f"[{prev}]",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", str(final)])
    return final


def main(scenes_path, work_dir, out_path):
    data = json.loads(Path(scenes_path).read_text())
    scenes = data["scenes"]
    events = data.get("events", [])
    work = Path(work_dir)
    timing = json.loads((work / "timing.json").read_text())
    ov_dir = work / "overlays"
    ov_dir.mkdir(parents=True, exist_ok=True)
    segdir = work / "segments"
    segdir.mkdir(parents=True, exist_ok=True)
    P = _paths(work)
    mk = marks_map(P['marks'])

    segs = []
    story_i = 0
    cuts = []            # (src, start, dur, timeline位置) プレイカットのゲーム音
    timeline = 0.0
    for i, (sc, tm) in enumerate(zip(scenes, timing)):
        dur = max(tm["dur"] + 0.5, 2.0) + XFADE
        dst = segdir / f"seg{i:02d}.mp4"
        kind = sc["kind"]

        if kind == "image":
            # story beats play over live gameplay so nothing sits static
            ov = ov_dir / f"{i:02d}.png"
            overlays.story_overlay(sc, sc["narration"],
                                   work / "imgs" / f"{i:02d}.png").save(ov)
            at = STORY_BED_AT[story_i % len(STORY_BED_AT)]
            story_i += 1
            # The story panel covers the left, and the runner sits mid-frame,
            # so pan the gameplay right to keep the ninja in the clear part.
            seg_clip(P['bed'], at, dur, ov, dst, pan=-0.28)
            game_src = None          # 物語カットは静かに
            what = "story"

        elif kind == "showcase":
            ov = ov_dir / f"{i:02d}.png"
            overlays.showcase_overlay(sc).save(ov)
            seg_clip(P['showcase'] / f"{sc['subject']}.mp4", 1.0, dur, ov, dst)
            game_src = None          # showcase は無音で撮っている
            what = "showcase:" + sc["subject"]

        elif kind == "outro":
            ov = ov_dir / f"{i:02d}.png"
            overlays.title_card(sc["title"], sc.get("subtitle")).save(ov)
            beat, lead = clip_source("run", mk, events)
            seg_clip(P['raw'], mk[beat] + lead, dur, ov, dst)
            game_src = (P['raw'], mk[beat] + lead)
            what = "outro"

        elif sc.get("clip"):
            clip = sc["clip"]
            beat, lead = clip_source(clip, mk, events)
            # the opening hook carries the one line of setup
            ov = None
            if kind == "hook":
                ov = ov_dir / f"{i:02d}.png"
                overlays.title_card("A complaint was filed in 1687.").save(ov)
            elif sc.get("title"):
                ov = ov_dir / f"{i:02d}.png"
                overlays.showcase_overlay(sc).save(ov)
            seg_clip(P['raw'], mk[beat] + lead, dur, ov, dst)
            game_src = (P['raw'], mk[beat] + lead)
            what = "clip:" + clip

        else:
            raise SystemExit(f"scene {i} ({kind}) has nothing to render")

        segs.append((dst, dur))
        # ゲーム音を入れるのはプレイ映像のカットだけ（静止画やshowcaseは無音）
        if game_src:      # プレイ映像を使ったカットすべて（outro含む）
            if game_src and has_audio(game_src[0]):
                cuts.append((game_src[0], game_src[1], dur, timeline))
        timeline += dur - XFADE      # クロスフェード分は重なる
        print(f"  seg{i:02d} {kind:10s} {what:20s} {dur:5.2f}s", flush=True)

    final = concat_xfade(segs, work, [sc['kind'] for sc in scenes])
    total = timeline + XFADE
    gtrack = game_audio_track(cuts, total, work, work / "game_audio.m4a")
    if gtrack:
        print(f"  ゲーム音を {len(cuts)} カットに敷きます", flush=True)
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final),
             "-i", str(work / "narration.wav"), "-i", str(gtrack),
             "-filter_complex",
             "[1:a]volume=1.0[nar];[2:a]apad[gm];"
             "[nar][gm]amix=inputs=2:duration=first:dropout_transition=0[a]",
             "-map", "0:v", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-shortest", str(out_path)])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final),
             "-i", str(work / "narration.wav"),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-shortest", str(out_path)])
    print(f"VIDEO_OK {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
