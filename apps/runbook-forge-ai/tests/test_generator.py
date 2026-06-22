from runbook_forge.generator import generate_runbook


def test_generate_runbook_creates_required_sections_and_extracts_commands():
    notes = """
    Client reported WordPress was returning 502 errors after deploy.
    kubectl get pods -n wordpress showed crashloopbackoff.
    Error: database connection refused.
    Fixed by restarting mysql and rolling deployment.
    kubectl rollout restart deployment/site -n wordpress
    Verified with curl -I https://example.com returning HTTP/2 200.
    """

    markdown = generate_runbook(
        title="WordPress 502 after deploy",
        system="Client WordPress",
        runbook_type="Incident Resolution",
        tags="wordpress,kubernetes,502",
        raw_notes=notes,
    )

    for heading in [
        "## Summary",
        "## Symptoms",
        "## Impact",
        "## Likely Root Cause",
        "## Resolution Steps",
        "## Commands Used",
        "## Verification",
        "## Prevention Checklist",
        "## Escalation / Follow-up",
    ]:
        assert heading in markdown

    assert "# WordPress 502 after deploy" in markdown
    assert "kubectl get pods -n wordpress" in markdown
    assert "kubectl rollout restart deployment/site -n wordpress" in markdown
    assert "Client WordPress" in markdown
