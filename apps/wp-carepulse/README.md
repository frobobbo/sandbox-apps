# WP CarePulse

Client-facing WordPress care monitoring/reporting MVP.

## Features
- Track sites and clients.
- Normalize bare site domains and mixed-case hosts to `https://` so duplicate entries do not split history and manual reports always show the canonical URL.
- Reject blank site names plus blank, hostless, or credential-style URLs before saving a site.
- Score uptime, SSL, latency, WordPress updates, backup freshness, and headers.
- Store latest checks in SQLite.
- Generate a monthly Markdown care report from the exact saved check results, preserving the recorded score and recommendations.
- Simple FastAPI/Jinja dashboard with recommended actions visible beside each latest check.

## Run
```bash
cd /opt/data/projects/brett-apps/apps/wp-carepulse
uv run pytest -q
uv run uvicorn wp_carepulse.main:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010
