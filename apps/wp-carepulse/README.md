# WP CarePulse

Client-facing WordPress care monitoring/reporting MVP.

## Features
- Track sites and clients.
- Run automated homepage, TLS certificate, latency, and security-header checks directly from the dashboard, or record a manual check when wp-admin data is available.
- Normalize bare site domains, mixed-case hosts, explicit default ports (`:443` for HTTPS and `:80` for HTTP), and URL fragments (such as `#contact`) so duplicate entries do not split history and both automatic and manual reports use the canonical URL.
- Refresh the saved site name and any provided client when an existing URL is added again, preserving both its check history and an existing client when the optional field is left blank.
- Reject blank site names plus blank, hostless, credential-style, or malformed-port URLs before saving a site.
- Restrict manual check HTTP status entries to the valid `100`–`599` range in both the dashboard and API.
- Reject impossible negative latency, SSL-days-remaining, update-count, and backup-age measurements in both the dashboard and API.
- Score uptime, SSL, latency, WordPress updates, backup freshness, and security headers, including HSTS, clickjacking protection, and `X-Content-Type-Options: nosniff`.
- Mark WordPress update and backup metrics from basic automated HTTP checks as unverified, show them as `Not checked` on the dashboard, and include a verification action in client reports instead of presenting placeholder zeroes as confirmed facts.
- Recommend enabling HTTPS for plain-HTTP sites without premature certificate-renewal or HSTS advice.
- Preserve actual HTTP error status codes (such as 404 or 503) and their response security headers in automated checks, while describing DNS, TLS, timeout, and connection failures as a missing HTTP response without inferring unverified SSL or security-header findings.
- Store latest checks in SQLite.
- Expose a storage-aware `/health` readiness endpoint that returns HTTP 503 when SQLite is unavailable.
- Generate a monthly Markdown care report from the exact saved check results, preserving the recorded score, recommendations, and a readable UTC timestamp for each site's latest check.
- Simple FastAPI/Jinja dashboard with recommended actions visible beside each latest check.

## Run
```bash
cd /opt/data/projects/brett-apps/apps/wp-carepulse
uv run pytest -q
uv run uvicorn wp_carepulse.main:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010
