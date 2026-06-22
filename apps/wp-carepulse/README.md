# WP CarePulse

Client-facing WordPress care monitoring/reporting MVP.

## Features
- Track sites and clients.
- Score uptime, SSL, latency, WordPress updates, backup freshness, and headers.
- Store latest checks in SQLite.
- Generate a monthly Markdown care report.
- Simple FastAPI/Jinja dashboard.

## Run
```bash
cd /opt/data/projects/wp-carepulse
uv run pytest -q
uv run uvicorn wp_carepulse.main:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010
