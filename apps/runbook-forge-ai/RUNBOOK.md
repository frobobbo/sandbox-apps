# Runbook Forge AI — Overnight Build Runbook

## Goal
Build a one-evening MVP of **Runbook Forge AI**: an AI-assisted app that turns raw troubleshooting notes, Kubernetes events, shell output, and incident notes into structured runbooks, with optional publishing to BookStack.

## Working directory
`/opt/data/projects/runbook-forge-ai`

## Product brief
- **User:** Brett Johnson
- **Primary use case:** Convert one-off ops fixes into repeatable BookStack documentation.
- **Target users:** Brett, WordPress hosting clients, church/homelab operations.
- **MVP shape:** Local web app, simple to deploy later to Kubernetes.

## MVP features
1. Web form for:
   - title
   - system/client
   - runbook type
   - tags
   - raw notes/output
2. Runbook generator that creates structured markdown with:
   - Summary
   - Symptoms
   - Impact
   - Likely Root Cause
   - Resolution Steps
   - Commands Used
   - Verification
   - Prevention Checklist
   - Escalation / Follow-up
3. Preview/edit page before saving or publishing.
4. SQLite history of generated runbooks.
5. BookStack publishing integration, configured by environment variables:
   - `BOOKSTACK_BASE_URL`
   - `BOOKSTACK_TOKEN_ID`
   - `BOOKSTACK_TOKEN_SECRET`
   - optional default `BOOKSTACK_BOOK_ID` / `BOOKSTACK_CHAPTER_ID`
6. Dockerfile and README for future homelab deployment.

## Preferred implementation
Use the simplest reliable stack available in this environment:
- Python 3.13
- FastAPI or Flask if dependencies are easy via `uv`
- Jinja/HTMX-style server-rendered templates
- SQLite
- OpenAI-compatible AI provider if configured; otherwise deterministic local template generator with clean TODOs for AI integration

## Build constraints
- Do not require secrets to run locally.
- Do not print secrets.
- Prefer a working non-AI fallback over a broken AI-only app.
- Verify with actual commands/tests before calling it done.
- Write a morning summary to `/opt/data/projects/runbook-forge-ai/MORNING_SUMMARY.md`.
- Keep all implementation logs in `/opt/data/projects/runbook-forge-ai/overnight-build.log`.

## Acceptance criteria
- App can start locally.
- A sample note can be converted into a structured runbook.
- Generated runbook is persisted in SQLite or a local data file.
- README documents setup, env vars, and usage.
- Tests or smoke checks prove the main path works.
- Morning summary includes:
  - what was built
  - files created/changed
  - commands/tests run and results
  - what works
  - blockers
  - next recommended steps

## BookStack target idea
- Shelf: Homelab Operations
- Book: Kubernetes / Rancher Operations
- Chapter: Runbooks
- Example page: Runbook Forge AI Setup and Usage

## Homelab deployment idea
```text
namespace: ops-tools
app: runbook-forge-ai
ingress: runbook-forge.johnsons.casa
database: sqlite PVC initially, Postgres later
```
