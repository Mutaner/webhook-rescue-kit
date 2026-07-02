from pathlib import Path

from webhook_rescue import ingest, store


def test_duplicate_stripe_event_does_not_double_count_credits(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/stripe_duplicate_events.json"))

    with store.connect(db) as conn:
        events = store.list_events(conn)
        account = store.get_account(conn, "cus_demo_001")

    assert [row["status"] for row in events] == ["accepted", "duplicate"]
    assert account is not None
    assert account["credits"] == 100

