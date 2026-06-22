from __future__ import annotations

from pathlib import Path
import shlex
import subprocess


def build_ffmpeg_command(
    input_path: str | Path,
    output_path: str | Path,
    *,
    start: float,
    end: float,
    vertical: bool = False,
    captions: str | None = None,
) -> list[str]:
    if end <= start:
        raise ValueError("end must be greater than start")
    duration = end - start
    filters: list[str] = []
    if vertical:
        # Crop/scale to 9:16 Shorts format. Works best for centered sermon footage.
        filters.append("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
    if captions:
        escaped = captions.replace("'", "\\'").replace(":", "\\:")
        filters.append(
            "drawtext="
            f"text='{escaped}':"
            "fontcolor=white:fontsize=54:borderw=4:bordercolor=black:"
            "x=(w-text_w)/2:y=h-(text_h*3)"
        )
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(input_path),
        "-t", str(duration),
    ]
    if filters:
        cmd += ["-vf", ",".join(filters)]
    cmd += ["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(output_path)]
    return cmd


def render_clip(
    input_path: str | Path,
    output_path: str | Path,
    *,
    start: float,
    end: float,
    vertical: bool = False,
    captions: str | None = None,
) -> subprocess.CompletedProcess:
    cmd = build_ffmpeg_command(input_path, output_path, start=start, end=end, vertical=vertical, captions=captions)
    return subprocess.run(cmd, text=True, capture_output=True, check=False)
