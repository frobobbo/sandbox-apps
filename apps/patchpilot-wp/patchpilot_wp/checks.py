from __future__ import annotations

import re
import time
from dataclasses import dataclass
from html import unescape
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ERROR_PATTERNS = [
    "fatal error",
    "parse error",
    "warning:",
    "wordpress database error",
    "there has been a critical error on this website",
    "uncaught error",
]


@dataclass(frozen=True)
class PageFetchResult:
    url: str
    http_status: int | None
    title: str | None
    body: str
    elapsed_ms: int
    error: str | None = None


@dataclass(frozen=True)
class PageCheckResult:
    url: str
    http_status: int | None
    title: str | None
    status: str
    warnings: list[str]
    elapsed_ms: int
    evidence_text: str
    screenshot_path: str | None = None


def extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return unescape(title) if title else None


def fetch_page(url: str, timeout: float = 10.0) -> PageFetchResult:
    start = time.monotonic()
    request = Request(url, headers={"User-Agent": "PatchPilotWP/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(250_000)
            charset = response.headers.get_content_charset() or "utf-8"
            body = raw.decode(charset, errors="replace")
            elapsed_ms = round((time.monotonic() - start) * 1000)
            return PageFetchResult(url, response.status, extract_title(body), body, elapsed_ms, None)
    except HTTPError as exc:
        raw = exc.read(250_000)
        body = raw.decode("utf-8", errors="replace")
        elapsed_ms = round((time.monotonic() - start) * 1000)
        return PageFetchResult(url, exc.code, extract_title(body), body, elapsed_ms, None)
    except (URLError, TimeoutError, OSError) as exc:
        elapsed_ms = round((time.monotonic() - start) * 1000)
        return PageFetchResult(url, None, None, "", elapsed_ms, str(exc))


def evaluate_page_result(fetch: PageFetchResult, baseline_title: str | None = None) -> PageCheckResult:
    warnings: list[str] = []
    status = "pass"

    if fetch.error:
        warnings.append(fetch.error)
        status = "fail"
    if fetch.http_status is None:
        warnings.append("No HTTP response was received")
        status = "fail"
    elif fetch.http_status >= 400:
        warnings.append(f"HTTP {fetch.http_status} returned")
        status = "fail"
    elif fetch.http_status >= 300:
        warnings.append(f"HTTP {fetch.http_status} redirect returned")
        status = "warn"

    body_lower = fetch.body.lower()
    if any(pattern in body_lower for pattern in ERROR_PATTERNS):
        warnings.append("PHP/WordPress error text was detected")
        status = "fail"

    if baseline_title and fetch.title and fetch.title.strip() != baseline_title.strip():
        warnings.append(f"Title changed from {baseline_title} to {fetch.title}")
        if status == "pass":
            status = "warn"
    elif baseline_title and not fetch.title:
        warnings.append(f"Expected title {baseline_title} was not found")
        if status == "pass":
            status = "warn"

    evidence_parts = [f"URL: {fetch.url}", f"HTTP: {fetch.http_status or 'none'}", f"Title: {fetch.title or 'missing'}"]
    if warnings:
        evidence_parts.append("Warnings: " + "; ".join(warnings))
    return PageCheckResult(fetch.url, fetch.http_status, fetch.title, status, warnings, fetch.elapsed_ms, " | ".join(evidence_parts))


def check_page(url: str, baseline_title: str | None = None) -> PageCheckResult:
    return evaluate_page_result(fetch_page(url), baseline_title=baseline_title)


def generate_run_report(run: dict, checks: list[dict]) -> str:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for check in checks:
        counts[check.get("status", "warn")] = counts.get(check.get("status", "warn"), 0) + 1
    total = len(checks)
    overall = "Passed" if counts["fail"] == 0 and counts["warn"] == 0 else "Passed with warnings" if counts["fail"] == 0 else "Follow-up needed"
    lines = [
        "# PatchPilot WP Maintenance Report",
        "",
        f"**Site:** {run.get('site_name', 'Unknown site')} ({run.get('site_url', '')})",
        f"**Client:** {run.get('client_name') or 'Not specified'}",
        f"**Run date:** {run.get('created_at', '')}",
        f"**Overall status:** {overall}",
        "",
        f"## Summary",
        f"{total} pages tested — {counts['pass']} passed, {counts['warn']} warning, {counts['fail']} failed.",
    ]
    if run.get("notes"):
        lines.extend(["", "## Maintenance notes", str(run["notes"])])
    lines.extend(["", "## Pages tested"])
    for check in checks:
        warnings = check.get("warnings", [])
        if isinstance(warnings, str):
            warnings = [warnings] if warnings else []
        lines.append(f"- **{check.get('label', check.get('url'))}** — {str(check.get('status', 'warn')).upper()} (HTTP {check.get('http_status') or 'none'}, title: {check.get('title') or 'missing'})")
        if warnings:
            for warning in warnings:
                lines.append(f"  - {warning}")
    lines.extend(["", "## Recommended follow-up"])
    if counts["fail"]:
        lines.append("Review failed pages before approving production updates.")
    elif counts["warn"]:
        lines.append("Review noted warnings, then proceed if the visible page content is acceptable.")
    else:
        lines.append("No visible breakage or WordPress/PHP error text was detected on the tested pages.")
    lines.append("")
    return "\n".join(lines)
