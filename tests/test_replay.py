from pathlib import Path
import socket

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


def test_replay_is_simulated_without_external_calls(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/shopify_failed_orders.json"))

    def fail_external_call(*args, **kwargs):
        raise AssertionError("external network call attempted")

    monkeypatch.setattr(socket, "create_connection", fail_external_call)

    result = replay.replay_event(db, "shopify_order_failed_timeout")

    assert result["status"] == "replayed"
    assert "no external API was called" in result["replay_result"]
