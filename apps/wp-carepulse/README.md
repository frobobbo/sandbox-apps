# WP CarePulse

Client-facing WordPress care monitoring/reporting MVP.

## Features
- Track sites and clients.
- Normalize bare site domains and mixed-case hosts to `https://` so duplicate entries do not split history.
- Reject blank, hostless, or credential-style URLs before saving a site.
- Score uptime, SSL, latency, WordPress updates, backup freshness, and headers.
- Store latest checks in SQLite.
- Generate a monthly Markdown care report.
- Simple FastAPI/Jinja dashboard.

## Run
```bash
cd /opt/data/projects/brett-apps/apps/wp-carepulse
uv run pytest -q
uv run uvicorn wp_carepulse.main:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010
