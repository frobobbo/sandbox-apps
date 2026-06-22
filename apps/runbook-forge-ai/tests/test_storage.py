from pathlib import Path

from runbook_forge.generator import generate_runbook
from runbook_forge.storage import RunbookStore


def test_runbook_store_saves_and_loads_generated_runbook(tmp_path: Path):
    db_path = tmp_path / "runbooks.sqlite3"
    store = RunbookStore(db_path)
    markdown = generate_runbook(
        title="AdGuard DNS outage",
        system="Homelab DNS",
        runbook_type="Troubleshooting",
        tags="dns,homelab",
        raw_notes="dig failed. systemctl restart AdGuardHome. verified with dig johnsons.casa.",
    )

    saved = store.create_runbook(
        title="AdGuard DNS outage",
        system="Homelab DNS",
        runbook_type="Troubleshooting",
        tags="dns,homelab",
        raw_notes="dig failed",
        markdown=markdown,
    )
    loaded = store.get_runbook(saved.id)
    all_runbooks = store.list_runbooks()

    assert loaded is not None
    assert loaded.id == saved.id
    assert loaded.title == "AdGuard DNS outage"
    assert "## Verification" in loaded.markdown
    assert len(all_runbooks) == 1
