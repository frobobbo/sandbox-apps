# WP FleetOps

Kubernetes/homelab-oriented WordPress fleet operations MVP.

## Features
- Store fleet snapshots for many WordPress sites.
- Calculate health scores.
- Generate critical/warning/info alerts.
- Produce Markdown maintenance reports with fleet-level average scoring.
- Export the latest dashboard as machine-readable JSON with fleet summary totals.
- Simple FastAPI/Jinja dashboard.
- Kubernetes-friendly `/health` and `/ready` probes; readiness returns HTTP 503 when a required template is missing.
- Reject negative operational metrics and non-HTTP(S) site URLs at snapshot submission.
- Canonicalize stored site names and URLs so mixed-case hosts or trailing slashes update the same fleet record.

## Run
```bash
cd /opt/data/projects/brett-apps/apps/wp-fleetops
uv run pytest -q
uv run uvicorn wp_fleetops.main:app --host 127.0.0.1 --port 8020
```

Open http://127.0.0.1:8020

Useful endpoints:
- `GET /report` returns the Markdown maintenance report.
- `GET /export.json` returns the latest dashboard rows plus `sites`, `critical_sites`, and `average_score` summary fields for automation.
