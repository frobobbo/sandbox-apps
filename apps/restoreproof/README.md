# RestoreProof

RestoreProof is a small FastAPI/Jinja/SQLite MVP for proving that backups are recoverable. It records protected sites, backup metadata, restore drill evidence, verification scoring, and client-ready Markdown reports.

## MVP features

- Register WordPress, church, or homelab sites that need backup proof.
- Record backup metadata: label, date, size, storage location, and notes.
- Capture restore drill evidence: restore target URL, homepage/admin responses, database import, media presence, key URL checks, and backup age.
- Score each restore as `verified`, `partial`, or `failed` with recommended actions.
- Generate a plain-English Markdown report suitable for client managed-hosting updates.

## Run locally

```bash
uv run uvicorn restoreproof.main:app --host 127.0.0.1 --port 8010
```

Then open <http://127.0.0.1:8010>.

By default, runtime data is stored in `data/restoreproof.sqlite3`. Override it with:

```bash
RESTOREPROOF_DB=/path/to/restoreproof.sqlite3 uv run uvicorn restoreproof.main:app
```

## Test

```bash
uv run pytest -q
```

## Example managed-service positioning

- $49/mo/site: backup inventory and monthly proof report.
- $99/mo/site: monthly restore drill with evidence summary.
- $199+/mo: business continuity package with recovery runbooks and restore targets.

## Future enhancements

- Docker Compose or Kubernetes restore executor.
- WP-CLI database and uploads import automation.
- Temporary namespace restore drills for Kubernetes-hosted WordPress.
- PDF report export and BookStack publishing.
