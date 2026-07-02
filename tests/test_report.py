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
    assert "## Duplicate Events Detected" in markdown
    assert "evt_test_001" in markdown
    assert "## Failed Events Captured" in markdown
    assert "shopify_order_failed_timeout" in markdown
    assert "## Replayed Events" in markdown
    assert "shopify_order_failed_missing_field" in markdown
    assert "## Subscription Desync Findings" in markdown
    assert "sub_desync_001" in markdown
    assert "## Limitations" in markdown

