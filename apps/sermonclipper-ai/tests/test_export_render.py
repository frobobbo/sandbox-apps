import json
from pathlib import Path

from sermonclipper.core import ClipIdea
from sermonclipper.export import clips_to_markdown, clips_to_jsonable, safe_slug
from sermonclipper.render import build_ffmpeg_command


def test_safe_slug_makes_filename_safe():
    assert safe_slug("God's Grace: Hope / Peace!") == "gods-grace-hope-peace"


def test_clips_to_markdown_contains_timestamps_and_metadata():
    clip = ClipIdea(
        title="Grace Hope",
        description="A sermon highlight about grace and hope.",
        start=65,
        end=125,
        score=42,
        reason="Keywords: grace, hope",
        hashtags=("#sermonclip", "#hope"),
        text="grace gives us hope",
    )
    md = clips_to_markdown("https://youtube.com/watch?v=abc123", [clip])
    assert "01:05–02:05" in md
    assert "Grace Hope" in md
    assert "#hope" in md
    assert "yt-dlp" in md


def test_clips_to_jsonable_round_trips_cleanly():
    clip = ClipIdea("Title", "Desc", 1, 61, 12.5, "Reason", ("#tag",), "text")
    data = clips_to_jsonable("video-id", [clip])
    encoded = json.dumps(data)
    assert "Title" in encoded
    assert data["clips"][0]["duration"] == 60


def test_build_ffmpeg_command_creates_vertical_captioned_clip_command(tmp_path):
    out = tmp_path / "clip.mp4"
    cmd = build_ffmpeg_command("input.mp4", out, start=10, end=70, vertical=True, captions="hello")
    joined = " ".join(map(str, cmd))
    assert "ffmpeg" in cmd[0]
    assert "-ss" in cmd
    assert str(out) in cmd
    assert "scale=1080:1920" in joined
