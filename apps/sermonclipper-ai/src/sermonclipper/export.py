from __future__ import annotations

from dataclasses import asdict
import re
from typing import Sequence

from .core import ClipIdea, format_timestamp


def safe_slug(value: str, max_len: int = 70) -> str:
    value = re.sub(r"(?<=\w)'(?=\w)", "", value.lower())
    slug = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return (slug[:max_len].strip("-") or "clip")


def clips_to_jsonable(source: str, clips: Sequence[ClipIdea]) -> dict:
    return {
        "source": source,
        "clips": [
            {
                **asdict(c),
                "hashtags": list(c.hashtags),
                "start_timestamp": format_timestamp(c.start),
                "end_timestamp": format_timestamp(c.end),
                "duration": round(c.duration, 2),
            }
            for c in clips
        ],
    }


def clips_to_markdown(source: str, clips: Sequence[ClipIdea]) -> str:
    lines = [
        "# SermonClipper AI Suggestions",
        "",
        f"Source: {source}",
        "",
        "These clips are ranked by sermon-highlight language, emotional/practical punch, and Shorts-friendly duration.",
        "",
    ]
    for idx, clip in enumerate(clips, 1):
        slug = safe_slug(clip.title)
        lines.extend([
            f"## {idx}. {clip.title}",
            "",
            f"- **Time:** {format_timestamp(clip.start)}–{format_timestamp(clip.end)}",
            f"- **Duration:** {int(round(clip.duration))} seconds",
            f"- **Score:** {clip.score:.1f}",
            f"- **Why this clip:** {clip.reason}",
            f"- **Description:** {clip.description}",
            f"- **Hashtags:** {' '.join(clip.hashtags)}",
            f"- **Suggested filename:** `{idx:02d}-{slug}.mp4`",
            "",
            "### Transcript excerpt",
            "",
            f"> {clip.text}",
            "",
            "### Render command template",
            "",
            "```bash",
            f"yt-dlp -f 'bv*+ba/b' -o source.%(ext)s '{source}'",
            f"sermonclipper render source.mp4 --start {int(clip.start)} --end {int(clip.end)} --output {idx:02d}-{slug}.mp4 --vertical --captions \"{clip.title}\"",
            "```",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"
