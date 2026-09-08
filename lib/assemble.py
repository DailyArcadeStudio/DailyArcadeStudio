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

# Which recorded beat each gameplay scene starts from, plus lead-in.
CLIP_SOURCE = {
    # the boss blade sweeps past within about a second of its trigger
    "boss":   ("boss", -0.2),
    "run":    ("run_start", 0.8),
    "events": ("surge", -0.6),       # rolls through surge -> wall -> blackout
    "death":  ("death", -2.2),       # lead in before the hit, then K.O.
}

# Where in the calm bed each story beat starts. The bed has no events and
# no deaths, so nothing under the narration pulls the eye off the story.
STORY_BED_AT = [2.0, 14.0, 28.0, 45.0]


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def marks_map(marks_path):
    return {name: t for name, t in json.loads(Path(marks_path).read_text())["marks"]}


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


def concat_xfade(segs, work):
    if len(segs) == 1:
        return segs[0][0]
    inputs = []
    for p, _ in segs:
        inputs += ["-i", str(p)]
    fc, prev, cum = [], "0:v", segs[0][1]
    for i in range(1, len(segs)):
        out = f"v{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:"
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
    scenes = json.loads(Path(scenes_path).read_text())["scenes"]
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
            what = "story"

        elif kind == "showcase":
            ov = ov_dir / f"{i:02d}.png"
            overlays.showcase_overlay(sc).save(ov)
            seg_clip(P['showcase'] / f"{sc['subject']}.mp4", 1.0, dur, ov, dst)
            what = "showcase:" + sc["subject"]

        elif kind == "outro":
            ov = ov_dir / f"{i:02d}.png"
            overlays.title_card(sc["title"], sc.get("subtitle")).save(ov)
            beat, lead = CLIP_SOURCE["run"]
            seg_clip(P['raw'], mk[beat] + lead, dur, ov, dst)
            what = "outro"

        elif sc.get("clip"):
            clip = sc["clip"]
            beat, lead = CLIP_SOURCE[clip]
            # the opening hook carries the one line of setup
            ov = None
            if kind == "hook":
                ov = ov_dir / f"{i:02d}.png"
                overlays.title_card("A complaint was filed in 1687.").save(ov)
            elif sc.get("title"):
                ov = ov_dir / f"{i:02d}.png"
                overlays.showcase_overlay(sc).save(ov)
            seg_clip(P['raw'], mk[beat] + lead, dur, ov, dst)
            what = "clip:" + clip

        else:
            raise SystemExit(f"scene {i} ({kind}) has nothing to render")

        segs.append((dst, dur))
        print(f"  seg{i:02d} {kind:10s} {what:20s} {dur:5.2f}s", flush=True)

    final = concat_xfade(segs, work)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final),
         "-i", str(work / "narration.wav"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", str(out_path)])
    print(f"VIDEO_OK {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
