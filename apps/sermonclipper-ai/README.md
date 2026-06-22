# SermonClipper AI

A small Python app for turning church sermon YouTube videos into Shorts/Reels clip suggestions.

## What it does

- Fetches a YouTube transcript when captions are available.
- Scores transcript windows for sermon-highlight language such as hope, grace, faith, promise, prayer, and Jesus.
- Avoids low-value announcement-style moments where possible.
- Exports `clips.json` and `clips.md` with timestamps, suggested titles, descriptions, hashtags, and render commands.
- Optionally renders local video files into 9:16 vertical clips with a simple caption overlay using `ffmpeg`.

## Quick start

```bash
cd /opt/data/sermonclipper-ai
uv run sermonclipper analyze --demo --output-dir demo-output
```

Analyze a real YouTube video:

```bash
uv run sermonclipper analyze 'https://youtube.com/watch?v=VIDEO_ID' --count 5 --output-dir output/VIDEO_ID
```

Render a suggested clip after downloading the source video:

```bash
yt-dlp -f 'bv*+ba/b' -o source.%(ext)s 'https://youtube.com/watch?v=VIDEO_ID'
uv run sermonclipper render source.mp4 --start 123 --end 183 --output clip-01.mp4 --vertical --captions "Grace Meets You Here"
```

## Output files

- `clips.json` — structured data for automation
- `clips.md` — human-friendly content plan and render command templates

## Notes

Native YouTube “Clips” are not reliably exposed through the public API, so this app focuses on producing edited clip files and metadata for YouTube Shorts/Reels workflows.
