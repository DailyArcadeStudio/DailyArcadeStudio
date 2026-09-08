"""Assemble the Ninja Dash video: slides + gameplay clips + narration.

Scenes with a "clip" key are cut out of the raw screen recording (the
marks file written by capture_ninja.py says where each beat starts);
the rest are still slides. Segments are crossfaded, then the narration
is muxed on top.

usage: python lib/assemble.py scenes.json work_dir out.mp4
       (expects work_dir/{timing.json,narration.wav} and slides/)
"""
import json
import subprocess
import sys
from pathlib import Path

FPS = 30
W, H = 1920, 1080
XFADE = 0.4

RAW = Path("/tmp/ninja_raw.mp4")
MARKS = Path("/tmp/ninja_marks.json")

# Which recorded beat each clip scene starts from, plus lead-in.
# The recording is only ~51s, so a scene whose narration outruns its
# beat is allowed to roll on into the following events — that reads as
# continuous play rather than a loop.
CLIP_SOURCE = {
    # the boss blade sweeps past within about a second of its trigger,
    # so the hook opens right on it rather than leading in
    "hook":   ("boss", -0.2),
    "run":    ("run_start", 0.8),    # clean running, no events yet
    "events": ("surge", -0.6),       # rolls through surge -> wall -> blackout
    "death":  ("death", -2.2),       # lead in before the hit, then K.O.
}


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def marks_map():
    data = json.loads(MARKS.read_text())
    return {name: t for name, t in data["marks"]}


def still_segment(png, dur, dst):
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png),
         "-t", f"{dur:.3f}", "-r", str(FPS),
         "-vf", f"scale={W}:{H},format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(dst)])


def clip_segment(start, dur, dst):
    """Cut from the raw recording and upscale 1280x720 -> 1920x1080."""
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(start,0):.3f}",
         "-i", str(RAW), "-t", f"{dur:.3f}", "-r", str(FPS),
         "-vf", f"scale={W}:{H}:flags=lanczos,format=yuv420p",
         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(dst)])


def concat_xfade(segs, work):
    """segs = [(path, dur)] -> one crossfaded mp4."""
    if len(segs) == 1:
        return segs[0][0]
    inputs = []
    for p, _ in segs:
        inputs += ["-i", str(p)]
    fc, prev, cum = [], "0:v", segs[0][1]
    for i in range(1, len(segs)):
        offset = cum - XFADE
        out = f"v{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:"
                  f"duration={XFADE}:offset={offset:.3f}[{out}]")
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
    slides_dir = work / "slides"
    segdir = work / "segments"
    segdir.mkdir(parents=True, exist_ok=True)
    mk = marks_map()

    segs = []
    for i, (sc, tm) in enumerate(zip(scenes, timing)):
        # each segment covers its narration plus the crossfade it loses
        dur = max(tm["dur"] + 0.5, 2.0) + XFADE
        dst = segdir / f"seg{i:02d}.mp4"
        clip = sc.get("clip")
        if clip:
            beat, lead = CLIP_SOURCE[clip]
            clip_segment(mk[beat] + lead, dur, dst)
        else:
            png = slides_dir / f"s{i:02d}_{sc['kind']}.png"
            still_segment(png, dur, dst)
        segs.append((dst, dur))
        print(f"  seg{i:02d} {sc['kind']:12s} {'CLIP ' + clip if clip else 'slide':16s} {dur:5.2f}s")

    final = concat_xfade(segs, work)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final),
         "-i", str(work / "narration.wav"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", str(out_path)])
    print(f"VIDEO_OK {out_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
