# Brett Apps

A monorepo of small automation, WordPress operations, church media, and documentation tools built with Hermes Agent.

## Apps

| Folder | Purpose |
|---|---|
| `apps/wp-carepulse` | Client-facing WordPress care monitoring and monthly report generator. |
| `apps/wp-fleetops` | Homelab/Kubernetes-oriented WordPress fleet operations dashboard. |
| `apps/runbook-forge-ai` | Turns ops notes and command output into structured runbooks. |
| `apps/sermonclipper-ai` | Analyzes sermon transcripts and generates short-form clip candidates. |

## Quick verification

```bash
cd apps/wp-carepulse && uv run pytest -q
cd ../wp-fleetops && uv run pytest -q
cd ../runbook-forge-ai && uv run pytest -q
cd ../sermonclipper-ai && uv run --with pytest pytest -q
```

## Notes

Runtime SQLite databases, virtualenvs, media files, and secrets are intentionally excluded.
