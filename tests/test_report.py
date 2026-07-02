from pathlib import Path

from webhook_rescue import ingest, replay, report


def test_report_is_generated_from_sqlite_state(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    output = tmp_path / "recovery_report.md"
    ingest.ingest_file(db, Path("samples/stripe_duplicate_events.json"))
    ingest.ingest_file(db, Path("samples/shopify_failed_orders.json"))
    ingest.ingest_file(db, Path("samples/subscription_desync.json"))
    replay.replay_event(db, "shopify_order_failed_missing_field")

    markdown = report.generate_report(db, output)

    assert output.exists()
    assert "# Stripe Duplicate Credit Guard Diagnostic" in markdown
    assert "## Stripe Duplicate Credit Findings" in markdown
    assert "Duplicate Stripe Object Event" in markdown
    assert "evt_test_invoice_001_b" in markdown
    assert "## Shopify Failed Order Recovery" in markdown
    assert "shopify_order_failed_timeout" in markdown
    assert "## Simulated Replayed Events" in markdown
    assert "shopify_order_failed_missing_field" in markdown
    assert "## Subscription Desync Findings" in markdown
    assert "sub_desync_001" in markdown
    assert "## What I would check in your repo" in markdown
    assert "## Acceptance criteria" in markdown
    assert "## No-Live-API / No-Secrets Safety Boundary" in markdown
