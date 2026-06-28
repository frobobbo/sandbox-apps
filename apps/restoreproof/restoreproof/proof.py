from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise ValueError("Please enter a valid URL with a host name.")
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Please enter a valid URL with a host name.")
    path = "" if parsed.path == "/" and not parsed.query and not parsed.fragment else parsed.path
    return urlunparse((scheme, netloc, path, "", parsed.query, parsed.fragment))


@dataclass(frozen=True)
class RestoreEvidence:
    name: str
    restore_target_url: str
    homepage_status: int
    admin_status: int
    database_imported: bool
    media_present: bool
    key_urls_passed: int
    key_urls_total: int
    backup_age_hours: int
    backup_size_mb: int
    notes: str = ""


@dataclass(frozen=True)
class RestoreAssessment:
    assessed_at: str
    status: str
    score: int
    summary: str
    actions: list[str]
    evidence: RestoreEvidence

    def to_dict(self) -> dict:
        data = asdict(self)
        data["evidence"] = asdict(self.evidence)
        return data


def bool_from_form(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def evaluate_restore(evidence: RestoreEvidence) -> RestoreAssessment:
    evidence = replace(evidence, restore_target_url=normalize_url(evidence.restore_target_url))
    if evidence.key_urls_total < 0 or evidence.key_urls_passed < 0:
        raise ValueError("Key URL counts cannot be negative.")
    if evidence.key_urls_total and evidence.key_urls_passed > evidence.key_urls_total:
        raise ValueError("Passed key URLs cannot exceed total key URLs.")
    if evidence.backup_age_hours < 0 or evidence.backup_size_mb < 0:
        raise ValueError("Backup age and size cannot be negative.")

    score = 100
    actions: list[str] = []

    if evidence.homepage_status != 200:
        score -= 30
        actions.append("Fix restored homepage response before claiming recovery success.")
    if evidence.admin_status not in {200, 301, 302, 403}:
        score -= 15
        actions.append("Verify wp-admin/login endpoint exists on the restored copy.")
    if not evidence.database_imported:
        score -= 35
        actions.append("Import and verify the database backup in the restore target.")
    if not evidence.media_present:
        score -= 15
        actions.append("Restore and spot-check the uploads/media directory.")
    if evidence.key_urls_total == 0:
        score -= 10
        actions.append("Add at least one key URL probe to prove important pages load.")
    else:
        failed_urls = evidence.key_urls_total - evidence.key_urls_passed
        if failed_urls:
            score -= min(25, failed_urls * 8)
            actions.append(f"Investigate {failed_urls} failing key URL probe(s).")
    if evidence.backup_age_hours > 72:
        score -= 12
        actions.append("Refresh backup cadence; latest verified backup is more than 72 hours old.")
    if evidence.backup_size_mb == 0:
        score -= 10
        actions.append("Record backup size so future restore drills can detect incomplete archives.")

    score = max(0, min(100, score))
    if score >= 90:
        status = "verified"
        summary = "Restore verified: the backup produced a working recovery target with strong evidence."
    elif score >= 70:
        status = "partial"
        summary = "Restore partially verified: recovery evidence is usable, but follow-up is required."
    else:
        status = "failed"
        summary = "Restore failed verification: do not rely on this backup until blockers are fixed."

    return RestoreAssessment(
        assessed_at=utc_now_iso(),
        status=status,
        score=score,
        summary=summary,
        actions=actions,
        evidence=evidence,
    )


def render_restore_report(site: dict, backup: dict, run: dict, assessment: RestoreAssessment) -> str:
    lines = [
        f"# RestoreProof Report: {site['name']}",
        "",
        f"Client: {site.get('client') or 'Internal'}",
        f"Production URL: {site['url']}",
        f"Restore target: {assessment.evidence.restore_target_url}",
        f"Backup: {backup['label']} ({backup['size_mb']} MB, {backup['storage_location']})",
        f"Run date: {run['started_at']}",
        "",
        f"## Result: {assessment.status.upper()} ({assessment.score}/100)",
        assessment.summary,
        "",
        "## Evidence",
        f"- Homepage status: {assessment.evidence.homepage_status}",
        f"- Admin/login status: {assessment.evidence.admin_status}",
        f"- Database imported: {'yes' if assessment.evidence.database_imported else 'no'}",
        f"- Media present: {'yes' if assessment.evidence.media_present else 'no'}",
        f"- Key URLs passed: {assessment.evidence.key_urls_passed}/{assessment.evidence.key_urls_total}",
        f"- Backup age at drill: {assessment.evidence.backup_age_hours} hours",
    ]
    if assessment.actions:
        lines.extend(["", "## Recommended actions"])
        lines.extend(f"- {action}" for action in assessment.actions)
    else:
        lines.extend(["", "## Recommended actions", "- No immediate recovery blockers found."])
    if assessment.evidence.notes:
        lines.extend(["", "## Operator notes", assessment.evidence.notes])
    return "\n".join(lines) + "\n"
