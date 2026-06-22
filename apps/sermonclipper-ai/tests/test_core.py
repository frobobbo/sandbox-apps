from sermonclipper.core import TranscriptSegment, build_windows, score_windows, suggest_clips, format_timestamp


def sample_segments():
    text = [
        (0, 10, "welcome everyone today we are reading from john chapter three"),
        (10, 10, "god loves the world and gave his only son so we can have hope"),
        (20, 10, "this is the kind of moment we need to remember when life is hard"),
        (30, 10, "our announcements are after service and the potluck is downstairs"),
        (40, 10, "but listen church this is the promise grace changes everything"),
        (50, 10, "when you feel alone the lord is near and his mercy is new"),
        (60, 10, "let us pray together and respond with faith this week"),
    ]
    return [TranscriptSegment(start=s, duration=d, text=t) for s, d, t in text]


def test_format_timestamp_outputs_youtube_style_time():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(65) == "01:05"
    assert format_timestamp(3723) == "1:02:03"


def test_build_windows_groups_transcript_into_target_length_ranges():
    windows = build_windows(sample_segments(), min_seconds=20, max_seconds=35)
    assert windows
    assert all(20 <= w.duration <= 35 for w in windows)
    assert windows[0].start == 0
    assert "god loves" in windows[0].text


def test_score_windows_prefers_sermon_highlight_language_over_announcements():
    windows = build_windows(sample_segments(), min_seconds=20, max_seconds=35)
    scored = score_windows(windows)
    top = scored[0]
    assert top.score > 0
    assert "hope" in top.text or "promise" in top.text or "grace" in top.text
    assert "potluck" not in top.title.lower()


def test_suggest_clips_returns_ranked_non_overlapping_clip_ideas():
    clips = suggest_clips(sample_segments(), count=2, min_seconds=20, max_seconds=35)
    assert len(clips) == 2
    assert clips[0].score >= clips[1].score
    assert clips[0].start < clips[0].end
    assert clips[0].title
    assert clips[0].description
    assert clips[0].hashtags
