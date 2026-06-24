# WP FleetOps

Kubernetes/homelab-oriented WordPress fleet operations MVP.

## Features
- Store fleet snapshots for many WordPress sites.
- Calculate health scores.
- Generate critical/warning/info alerts.
- Produce Markdown maintenance reports.
- Simple FastAPI/Jinja dashboard.
- Reject negative operational metrics at snapshot submission.

## Run
```bash
cd /opt/data/projects/wp-fleetops
uv run pytest -q
uv run uvicorn wp_fleetops.main:app --host 127.0.0.1 --port 8020
```

Open http://127.0.0.1:8020
