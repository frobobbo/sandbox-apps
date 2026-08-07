# WP FleetOps

Kubernetes/homelab-oriented WordPress fleet operations MVP.

## Features
- Store fleet snapshots for many WordPress sites.
- Calculate health scores.
- Generate critical/warning/info alerts, including a critical escalation at 10 pending WordPress updates, a 30-day SSL renewal warning window, backup-age warnings after 36 hours that escalate to critical after 72 hours, and homepage latency warnings above 1.5 seconds that escalate to critical at 5 seconds.
- Produce Markdown maintenance reports with fleet-level average scoring, alert totals by severity, lowest-scoring sites listed first, and any site with a critical alert clearly marked as needing attention regardless of its numeric score.
- Export the latest dashboard as machine-readable JSON with fleet summary totals, including alert counts by severity.
- Download spreadsheet-ready CSV fleet rows with alert counts and formula-injection protection.
- Simple FastAPI/Jinja dashboard with defensive content-type, framing, referrer, and Content Security Policy headers, plus `Cache-Control: no-store` to prevent stale fleet data from being cached.
- Kubernetes-friendly `/health` and `/ready` probes; readiness returns HTTP 503 with dependency statuses when the database is unavailable or a required template is missing.
- Reject blank site names, site names over 200 characters, URLs over 2,048 characters, negative or SQLite-out-of-range operational metrics, non-HTTP(S) site URLs, malformed URLs without a hostname or valid port, and URLs containing embedded credentials before snapshots can be persisted or exported. The dashboard form advertises the same text limits for immediate browser feedback.
- Record an unchecked uptime checkbox as a down site so outage snapshots trigger critical alerts.
- Canonicalize stored site names and URLs so mixed-case hosts, trailing slashes, or explicit HTTP/HTTPS default ports update the same fleet record.

## Run
```bash
cd /opt/data/projects/brett-apps/apps/wp-fleetops
uv run pytest -q
uv run uvicorn wp_fleetops.main:app --host 127.0.0.1 --port 8020
```

Open http://127.0.0.1:8020

Useful endpoints:
- `GET /report` returns the Markdown maintenance report.
- `GET /export.json` returns the latest dashboard rows plus `sites`, `critical_sites`, `average_score`, and nested critical/warning/info `alerts` summary fields for automation.
- `GET /export.csv` downloads the latest fleet rows, operational metrics, alert counts, and capture timestamps as `wp-fleetops.csv`.
