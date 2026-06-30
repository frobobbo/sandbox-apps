# PatchPilot WP

PatchPilot WP is a small FastAPI/Jinja/SQLite MVP for WordPress maintenance evidence. It helps a freelancer record client sites, define key URLs, run page health checks before/after manual WordPress updates, and generate client-ready Markdown reports.

## MVP features

- Add/list WordPress sites and client names.
- Add key URLs/pages with optional baseline page titles.
- Start a maintenance run after manual plugin/theme/core update work.
- Run page checks for HTTP status, page title changes, broken/missing pages, and obvious WordPress/PHP error text.
- Store evidence rows in SQLite tables: `sites`, `site_pages`, `maintenance_runs`, `page_checks`, and `reports`.
- Generate a client-friendly Markdown/plain-text report at `/runs/{run_id}/report`.
- `/health` endpoint for uptime checks.

Screenshots are represented by a nullable `screenshot_path` field but are not captured in this first MVP. Playwright screenshot capture is the next enhancement once browser dependencies are available.

## Run locally

```bash
cd /opt/data/projects/brett-apps/apps/patchpilot-wp
uv run uvicorn patchpilot_wp.main:app --host 127.0.0.1 --port 8037
```

Open <http://127.0.0.1:8037/>.

## Test

```bash
cd /opt/data/projects/brett-apps/apps/patchpilot-wp
uv run --dev pytest -q
```

## Data

The default SQLite database is created at `data/patchpilot.sqlite3`. Tests monkeypatch the store to temporary databases.

## Docker

```bash
docker build -t patchpilot-wp .
docker run --rm -p 8037:8037 -v "$PWD/data:/app/data" patchpilot-wp
```
