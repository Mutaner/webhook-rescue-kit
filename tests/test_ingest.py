from pathlib import Path

from webhook_rescue import ingest, store


def test_shopify_failed_events_are_stored_as_replay_candidates(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/shopify_failed_orders.json"))

    with store.connect(db) as conn:
        ok = store.get_latest_event(conn, "shopify_order_ok_001")
        missing = store.get_latest_event(conn, "shopify_order_failed_missing_field")
        timeout = store.get_latest_event(conn, "shopify_order_failed_timeout")

    assert ok["status"] == "accepted"
    assert missing["status"] == "replay_pending"
    assert missing["failure_reason"] == "missing required order email"
    assert timeout["status"] == "replay_pending"
    assert timeout["failure_reason"] == "handler timeout"


def test_subscription_desync_is_detected_and_persisted(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/subscription_desync.json"))

    with store.connect(db) as conn:
        event = store.get_latest_event(conn, "sub_desync_001")
        account = store.get_account(conn, "cus_demo_001")

    assert event["status"] == "desync"
    assert "Local subscription is inactive" in event["failure_reason"]
    assert account is not None
    assert account["subscription_status_local"] == "inactive"
    assert account["subscription_status_provider"] == "active"

