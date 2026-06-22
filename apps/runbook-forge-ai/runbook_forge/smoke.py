from __future__ import annotations

import os
from pathlib import Path

from runbook_forge.generator import generate_runbook
from runbook_forge.storage import RunbookStore


def main() -> None:
    db_path = Path(os.getenv("RUNBOOK_FORGE_DB", "data/smoke-runbooks.sqlite3"))
    if db_path.exists():
        db_path.unlink()
    store = RunbookStore(db_path)
    raw_notes = """
    WordPress checkout returned 502 after plugin update.
    kubectl get pods -n client-site showed nginx running and php-fpm CrashLoopBackOff.
    journalctl -u php-fpm showed missing extension.
    Fixed by disabling the plugin and restarting php-fpm.
    kubectl rollout restart deployment/client-site -n client-site
    Verified with curl -I https://client.example returning HTTP/2 200.
    """
    markdown = generate_runbook(
        title="Smoke Test WordPress 502",
        system="Client WordPress",
        runbook_type="Incident Resolution",
        tags="wordpress,smoke-test",
        raw_notes=raw_notes,
    )
    record = store.create_runbook(
        title="Smoke Test WordPress 502",
        system="Client WordPress",
        runbook_type="Incident Resolution",
        tags="wordpress,smoke-test",
        raw_notes=raw_notes,
        markdown=markdown,
    )
    loaded = store.get_runbook(record.id)
    assert loaded is not None
    assert "## Summary" in loaded.markdown
    assert "## Commands Used" in loaded.markdown
    assert "kubectl rollout restart deployment/client-site -n client-site" in loaded.markdown
    print(f"SMOKE OK: saved runbook id={loaded.id} to {db_path}")


if __name__ == "__main__":
    main()
