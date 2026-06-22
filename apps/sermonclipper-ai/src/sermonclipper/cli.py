from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import suggest_clips
from .export import clips_to_jsonable, clips_to_markdown
from .render import render_clip
from .transcript import fetch_youtube_transcript, demo_transcript


def analyze_command(args: argparse.Namespace) -> int:
    if args.demo:
        segments = demo_transcript()
        source = "demo-sermon"
    else:
        if not args.url:
            print("Provide a YouTube URL/video ID or use --demo", file=sys.stderr)
            return 2
        segments = fetch_youtube_transcript(args.url, languages=args.languages.split(",") if args.languages else ["en"])
        source = args.url
    clips = suggest_clips(segments, count=args.count, min_seconds=args.min_seconds, max_seconds=args.max_seconds)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    data = clips_to_jsonable(source, clips)
    (outdir / "clips.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (outdir / "clips.md").write_text(clips_to_markdown(source, clips), encoding="utf-8")
    print(json.dumps({"status": "ok", "clips": len(clips), "output_dir": str(outdir), "files": ["clips.json", "clips.md"]}, indent=2))
    return 0


def render_command(args: argparse.Namespace) -> int:
    result = render_clip(
        args.input,
        args.output,
        start=args.start,
        end=args.end,
        vertical=args.vertical,
        captions=args.captions,
    )
    if result.returncode != 0:
        print(result.stderr[-4000:], file=sys.stderr)
        return result.returncode
    print(json.dumps({"status": "rendered", "output": args.output}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sermonclipper",
        description="Find sermon highlight clips from YouTube transcripts and optionally render Shorts/Reels clips.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Analyze a YouTube transcript and output clip suggestions")
    analyze.add_argument("url", nargs="?", help="YouTube URL or 11-character video ID")
    analyze.add_argument("--demo", action="store_true", help="Use built-in demo sermon transcript")
    analyze.add_argument("--count", type=int, default=5)
    analyze.add_argument("--min-seconds", type=int, default=35)
    analyze.add_argument("--max-seconds", type=int, default=90)
    analyze.add_argument("--languages", default="en", help="Comma-separated language fallback list, default: en")
    analyze.add_argument("--output-dir", default="sermonclipper-output")
    analyze.set_defaults(func=analyze_command)

    render = sub.add_parser("render", help="Render a clip from a local video file using ffmpeg")
    render.add_argument("input", help="Input video file")
    render.add_argument("--start", type=float, required=True)
    render.add_argument("--end", type=float, required=True)
    render.add_argument("--output", required=True)
    render.add_argument("--vertical", action="store_true", help="Output 9:16 vertical video for Shorts/Reels")
    render.add_argument("--captions", help="Simple title/caption overlay text")
    render.set_defaults(func=render_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
