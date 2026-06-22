from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

from .core import TranscriptSegment

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(value: str) -> str:
    raw = value.strip()
    if VIDEO_ID_RE.match(raw):
        return raw
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        vid = parsed.path.strip("/").split("/")[0]
        if VIDEO_ID_RE.match(vid):
            return vid
    if "youtube" in host:
        qs = parse_qs(parsed.query)
        if qs.get("v") and VIDEO_ID_RE.match(qs["v"][0]):
            return qs["v"][0]
        parts = [p for p in parsed.path.split("/") if p]
        for key in ("shorts", "embed", "live"):
            if key in parts:
                idx = parts.index(key)
                if idx + 1 < len(parts) and VIDEO_ID_RE.match(parts[idx + 1]):
                    return parts[idx + 1]
    raise ValueError(f"Could not extract YouTube video id from: {value}")


def fetch_youtube_transcript(url_or_id: str, languages: list[str] | None = None) -> list[TranscriptSegment]:
    """Fetch transcript using youtube-transcript-api with compatibility across versions."""
    video_id = extract_video_id(url_or_id)
    languages = languages or ["en"]
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise RuntimeError("youtube-transcript-api is not installed. Run: uv sync") from exc

    raw_items = None
    # Newer API shape.
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=languages)
        raw_items = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
    except Exception:
        # Older API shape.
        try:
            raw_items = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        except Exception as exc:
            raise RuntimeError(f"Could not fetch transcript for {video_id}: {exc}") from exc

    segments: list[TranscriptSegment] = []
    for item in raw_items or []:
        text = item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
        start = item.get("start", 0) if isinstance(item, dict) else getattr(item, "start", 0)
        duration = item.get("duration", 0) if isinstance(item, dict) else getattr(item, "duration", 0)
        text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
        if text:
            segments.append(TranscriptSegment(float(start), float(duration), text))
    if not segments:
        raise RuntimeError(f"Transcript for {video_id} was empty")
    return segments


def demo_transcript() -> list[TranscriptSegment]:
    samples = [
        (0, 8, "Welcome church family today we are opening God's word together."),
        (8, 10, "In John chapter three we hear that God so loved the world."),
        (18, 10, "That means hope is not wishful thinking, hope is rooted in Jesus."),
        (28, 10, "Please remember the potluck and announcements after the service."),
        (38, 10, "But don't miss this promise: grace meets you in the middle of your failure."),
        (48, 10, "When you feel alone, the Lord is near, and mercy is new every morning."),
        (58, 10, "So respond with faith this week and take one step of obedience."),
        (68, 10, "Let us pray and ask God to make this truth real in our hearts."),
    ]
    return [TranscriptSegment(start=s, duration=d, text=t) for s, d, t in samples]
