from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Sequence


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    duration: float
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass(frozen=True)
class ClipWindow:
    start: float
    end: float
    text: str
    segments: tuple[TranscriptSegment, ...]

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class ClipIdea:
    title: str
    description: str
    start: float
    end: float
    score: float
    reason: str
    hashtags: tuple[str, ...]
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start


POSITIVE_TERMS = {
    "god": 4, "jesus": 4, "christ": 4, "lord": 4, "spirit": 3,
    "grace": 5, "mercy": 4, "hope": 5, "faith": 4, "love": 4,
    "promise": 5, "truth": 3, "forgive": 4, "forgiveness": 4,
    "redeem": 4, "redemption": 4, "salvation": 4, "prayer": 3,
    "pray": 3, "worship": 3, "scripture": 3, "bible": 3,
    "listen": 3, "remember": 3, "life": 2, "heart": 2, "peace": 4,
    "alone": 2, "hard": 2, "changes": 3, "respond": 3,
}
NEGATIVE_TERMS = {
    "announcement": -6, "announcements": -6, "potluck": -6, "offering": -2,
    "parking": -5, "bathroom": -5, "downstairs": -5, "calendar": -4,
    "newsletter": -4, "subscribe": -2,
}
TITLE_STOPWORDS = {
    "the", "and", "but", "for", "you", "your", "are", "that", "this", "with",
    "from", "have", "when", "into", "will", "need", "life", "today", "church",
    "everyone", "chapter", "reading", "only", "gave", "feel", "week", "lets",
}


def format_timestamp(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_windows(
    segments: Sequence[TranscriptSegment],
    min_seconds: int = 35,
    max_seconds: int = 90,
    step_seconds: int | None = None,
) -> list[ClipWindow]:
    """Build overlapping windows from transcript segments."""
    clean = [s for s in sorted(segments, key=lambda x: x.start) if s.text.strip()]
    if not clean:
        return []
    if min_seconds <= 0 or max_seconds < min_seconds:
        raise ValueError("Require 0 < min_seconds <= max_seconds")
    step = step_seconds or max(10, min_seconds // 2)
    windows: list[ClipWindow] = []
    i = 0
    while i < len(clean):
        start = clean[i].start
        group: list[TranscriptSegment] = []
        end = start
        j = i
        while j < len(clean):
            seg = clean[j]
            if seg.end - start > max_seconds and (end - start) >= min_seconds:
                break
            group.append(seg)
            end = max(end, seg.end)
            if (end - start) >= min_seconds and (j + 1 == len(clean) or clean[j + 1].end - start > max_seconds):
                break
            j += 1
        if group and min_seconds <= end - start <= max_seconds:
            text = normalize_text(" ".join(s.text for s in group))
            windows.append(ClipWindow(start=start, end=end, text=text, segments=tuple(group)))
        # advance to first segment at or after start + step
        next_start = start + step
        ni = i + 1
        while ni < len(clean) and clean[ni].start < next_start:
            ni += 1
        i = max(i + 1, ni)
    return windows


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _keyword_score(tokens: Iterable[str]) -> tuple[float, list[str]]:
    score = 0.0
    hits: list[str] = []
    for t in tokens:
        if t in POSITIVE_TERMS:
            score += POSITIVE_TERMS[t]
            hits.append(t)
        if t in NEGATIVE_TERMS:
            score += NEGATIVE_TERMS[t]
    return score, sorted(set(hits))


def _make_title(text: str) -> str:
    tokens = [t for t in _tokenize(text) if t not in TITLE_STOPWORDS and len(t) > 2]
    priority = sorted(set(tokens), key=lambda t: (POSITIVE_TERMS.get(t, 0), len(t)), reverse=True)
    if priority:
        words = priority[:5]
        return " ".join(w.capitalize() for w in words)
    first = normalize_text(text).split(".")[0][:60]
    return first.strip().title() or "Sermon Highlight"


def _make_description(clip: ClipWindow, keywords: list[str]) -> str:
    first = normalize_text(clip.text)
    if len(first) > 180:
        first = first[:177].rsplit(" ", 1)[0] + "..."
    if keywords:
        return f"A sermon highlight about {', '.join(keywords[:4])}: {first}"
    return f"A short sermon highlight: {first}"


def score_windows(windows: Sequence[ClipWindow]) -> list[ClipIdea]:
    ideas: list[ClipIdea] = []
    for w in windows:
        tokens = _tokenize(w.text)
        kw_score, keywords = _keyword_score(tokens)
        # prefer clip lengths useful for Shorts/Reels: 35-75 seconds, but allow shorter tests/MVP
        length_bonus = 8 if 35 <= w.duration <= 75 else 3 if 20 <= w.duration < 35 else 0
        sentence_bonus = min(6, len(re.findall(r"\b(remember|listen|promise|hope|grace|faith|pray|respond)\b", w.text.lower())) * 2)
        score = kw_score + length_bonus + sentence_bonus
        title = _make_title(w.text)
        hashtags = ("#sermonclip", "#faith", "#church")
        if "prayer" in keywords or "pray" in keywords:
            hashtags += ("#prayer",)
        if "hope" in keywords:
            hashtags += ("#hope",)
        if "grace" in keywords:
            hashtags += ("#grace",)
        ideas.append(ClipIdea(
            title=title,
            description=_make_description(w, keywords),
            start=w.start,
            end=w.end,
            score=score,
            reason=f"Keywords: {', '.join(keywords[:8]) or 'general sermon language'}; duration {int(w.duration)}s",
            hashtags=hashtags,
            text=w.text,
        ))
    return sorted(ideas, key=lambda c: (c.score, -abs(c.duration - 60)), reverse=True)


def _overlaps(a: ClipIdea, b: ClipIdea, padding: float = 5) -> bool:
    return not (a.end + padding <= b.start or b.end + padding <= a.start)


def suggest_clips(
    segments: Sequence[TranscriptSegment],
    count: int = 5,
    min_seconds: int = 35,
    max_seconds: int = 90,
) -> list[ClipIdea]:
    windows = build_windows(segments, min_seconds=min_seconds, max_seconds=max_seconds)
    ranked = score_windows(windows)
    chosen: list[ClipIdea] = []
    for idea in ranked:
        if idea.score <= 0:
            continue
        if all(not _overlaps(idea, existing) for existing in chosen):
            chosen.append(idea)
        if len(chosen) >= count:
            break
    return chosen
