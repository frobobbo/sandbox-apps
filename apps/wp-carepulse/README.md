# WP CarePulse

Client-facing WordPress care monitoring/reporting MVP.

## Features
- Track sites and clients.
- Normalize bare site domains and mixed-case hosts to `https://` so duplicate entries do not split history and manual reports always show the canonical URL.
- Reject blank site names plus blank, hostless, or credential-style URLs before saving a site.
- Restrict manual check HTTP status entries to the valid `100`–`599` range in both the dashboard and API.
- Reject impossible negative latency, SSL-days-remaining, update-count, and backup-age measurements in both the dashboard and API.
- Score uptime, SSL, latency, WordPress updates, backup freshness, and headers.
- Preserve actual HTTP error status codes (such as 404 or 503) in automated checks instead of reporting them as generic connection failures.
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
