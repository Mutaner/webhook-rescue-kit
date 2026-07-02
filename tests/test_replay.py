from pathlib import Path

from webhook_rescue import ingest, replay, store


def test_replay_updates_pending_event_status(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/shopify_failed_orders.json"))

    result = replay.replay_event(db, "shopify_order_failed_timeout")

    with store.connect(db) as conn:
        row = store.get_latest_event(conn, "shopify_order_failed_timeout")

    assert result["status"] == "replayed"
    assert row["status"] == "replayed"
    assert row["replayed_at"] is not None
    assert "simulated local replay succeeded" in row["replay_result"]

