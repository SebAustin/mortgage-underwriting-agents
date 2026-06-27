"""Assemble the demo video: narrate each scene with macOS ``say``, then mux with ffmpeg.

For every scene in ``manifest.json`` it (1) renders narration to AIFF via ``say``,
(2) measures the clip length (narration + tail, floored at the scene minimum), (3) builds a
still+audio H.264 clip, then concatenates all clips into ``video/demo.mp4``. Re-runnable.
"""

from __future__ import annotations

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, "frames")
AUDIO = os.path.join(HERE, "audio")
CLIPS = os.path.join(HERE, "clips")
OUT = os.path.join(HERE, "demo.mp4")
VOICE = os.environ.get("DEMO_VOICE", "Samantha")
TAIL = 1.8  # seconds of held frame after narration ends (reading buffer)
LEAD = 0.35  # seconds of silence before narration starts
MIN_CLIP = 6.0  # floor so very short scenes still breathe


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def duration(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]
    )
    return float(out.decode().strip())


def voice_ok(voice: str) -> bool:
    try:
        names = subprocess.check_output(["say", "-v", "?"]).decode()
        return any(line.split()[0] == voice for line in names.splitlines() if line.strip())
    except Exception:
        return False


def main() -> None:
    os.makedirs(AUDIO, exist_ok=True)
    os.makedirs(CLIPS, exist_ok=True)
    manifest = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
    voice = VOICE if voice_ok(VOICE) else None  # None → default system voice

    clip_paths: list[str] = []
    total = 0.0
    for sc in manifest:
        name = sc["id"]
        frame = os.path.join(FRAMES, f"{name}.png")
        aiff = os.path.join(AUDIO, f"{name}.aiff")
        clip = os.path.join(CLIPS, f"{name}.mp4")

        say = ["say", "-o", aiff]
        if voice:
            say += ["-v", voice]
        say.append(sc["speak"])
        run(say)

        narr = duration(aiff)
        # Narration-driven length (+ a reading tail), floored — avoids long silent holds.
        clip_len = max(narr + LEAD + TAIL, MIN_CLIP)

        # Still image for clip_len; narration delayed by LEAD, padded to clip_len.
        run([
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30", "-t", f"{clip_len:.3f}", "-i", frame,
            "-i", aiff,
            "-filter_complex",
            f"[0:v]scale=1920:1080,format=yuv420p,fps=30[v];"
            f"[1:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad,atrim=0:{clip_len:.3f}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            clip,
        ])
        clip_paths.append(clip)
        total += clip_len
        print(f"  {name:18} narr {narr:5.1f}s  clip {clip_len:5.1f}s")

    concat_list = os.path.join(CLIPS, "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as fh:
        for p in clip_paths:
            fh.write(f"file '{p}'\n")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", OUT,
    ])
    mins = int(total // 60)
    secs = int(total % 60)
    size_mb = os.path.getsize(OUT) / 1e6
    print(f"\n✓ {OUT}")
    print(f"  total ~{mins}:{secs:02d}  ({total:.1f}s) · {size_mb:.1f} MB · voice={voice or 'default'}")


if __name__ == "__main__":
    main()
