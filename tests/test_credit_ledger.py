from webhook_rescue.credit_ledger import (
    build_credit_operation_hash,
    build_stripe_event_hash,
    classify_credit_webhook,
)


def test_duplicate_checkout_session_completed_recredits_workspace() -> None:
    result = classify_credit_webhook(
        existing_event={"state": "credited"},
        existing_credit=None,
        incoming={"event_type": "checkout.session.completed"},
    )

    assert result == "return_already_processed_no_credit_delta"


def test_same_payment_object_different_stripe_event_delivery() -> None:
    result = classify_credit_webhook(
        existing_event=None,
        existing_credit={"state": "credited"},
        incoming={"stripe_payment_object_id": "pi_credit_demo_001"},
    )

    assert result == "return_existing_credit_record_no_balance_increment"


def test_duplicate_event_while_first_processing_in_flight() -> None:
    result = classify_credit_webhook(
        existing_event={"state": "in_flight"},
        existing_credit=None,
        incoming={"event_id": "evt_credit_demo_001"},
    )

    assert result == "return_409_or_wait_for_original_processing"


def test_first_valid_topup_event() -> None:
    result = classify_credit_webhook(
        existing_event=None,
        existing_credit=None,
        incoming={"event_id": "evt_credit_demo_001"},
    )

    assert result == "claim_event_and_apply_credit_once"


def test_same_event_failed_before_credit() -> None:
    result = classify_credit_webhook(
        existing_event={"state": "failed_before_credit"},
        existing_credit=None,
        incoming={"event_id": "evt_credit_demo_001"},
    )

    assert result == "safe_retry_same_event"


def test_same_input_returns_same_hash() -> None:
    first = build_stripe_event_hash("evt_credit_demo_001", "invoice.paid", False)
    second = build_stripe_event_hash("evt_credit_demo_001", "invoice.paid", False)

    assert first == second


def test_different_livemode_changes_stripe_event_hash() -> None:
    testmode = build_stripe_event_hash("evt_credit_demo_001", "invoice.paid", False)
    livemode = build_stripe_event_hash("evt_credit_demo_001", "invoice.paid", True)

    assert testmode != livemode


def test_different_credit_type_changes_credit_operation_hash() -> None:
    topup = build_credit_operation_hash(
        "workspace_credit_demo_001",
        "invoice_credit_demo_001",
        "manual",
        1000,
        "usd",
        "topup",
    )
    promotional = build_credit_operation_hash(
        "workspace_credit_demo_001",
        "invoice_credit_demo_001",
        "manual",
        1000,
        "usd",
        "promotional",
    )

    assert topup != promotional


def test_different_amount_changes_credit_operation_hash() -> None:
    smaller = build_credit_operation_hash(
        "workspace_credit_demo_001",
        "invoice_credit_demo_001",
        "manual",
        1000,
        "usd",
        "topup",
    )
    larger = build_credit_operation_hash(
        "workspace_credit_demo_001",
        "invoice_credit_demo_001",
        "manual",
        2000,
        "usd",
        "topup",
    )

    assert smaller != larger
