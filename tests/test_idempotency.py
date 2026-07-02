from pathlib import Path

from webhook_rescue import ingest, store


def test_same_stripe_event_id_does_not_double_count_credits(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/stripe_duplicate_events.json"))

    with store.connect(db) as conn:
        events = store.list_events(conn)
        account = store.get_account(conn, "cus_credit_demo_001")

    assert [row["status"] for row in events] == [
        "accepted",
        "duplicate",
        "duplicate_object",
    ]
    assert account is not None
    assert account["credits"] == 100


def test_same_stripe_object_id_with_different_event_id_does_not_double_count_credits(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/stripe_duplicate_events.json"))

    with store.connect(db) as conn:
        object_duplicate = store.get_latest_event(conn, "evt_test_invoice_001_b")
        account = store.get_account(conn, "cus_credit_demo_001")

    assert object_duplicate["status"] == "duplicate_object"
    assert object_duplicate["duplicate_of_event_id"] == "evt_test_invoice_001_a"
    assert object_duplicate["credit_delta"] == 0
    assert account is not None
    assert account["credits"] == 100


def test_desync_account_is_separate_from_credit_demo_account(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    ingest.ingest_file(db, Path("samples/stripe_duplicate_events.json"))
    ingest.ingest_file(db, Path("samples/subscription_desync.json"))

    with store.connect(db) as conn:
        credit_account = store.get_account(conn, "cus_credit_demo_001")
        desync_account = store.get_account(conn, "cus_desync_demo_001")

    assert credit_account is not None
    assert credit_account["credits"] == 100
    assert credit_account["subscription_status_local"] is None
    assert desync_account is not None
    assert desync_account["credits"] == 0
    assert desync_account["subscription_status_local"] == "inactive"
