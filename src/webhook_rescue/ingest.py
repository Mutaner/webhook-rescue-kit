from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from webhook_rescue.models import SampleEvent
from webhook_rescue import store


STRIPE_CREDIT_TYPES = {"invoice.paid", "checkout.session.completed"}


def load_sample_events(path: Path) -> list[SampleEvent]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    raw_events = data.get("events", data)
    return [SampleEvent.from_dict(item) for item in raw_events]


def ingest_file(db_path: Path, sample_path: Path) -> list[dict[str, str]]:
    store.init_db(db_path)
    results: list[dict[str, str]] = []
    with store.connect(db_path) as conn:
        for event in load_sample_events(sample_path):
            row = ingest_event(conn, event)
            results.append({"event_id": row["event_id"], "status": row["status"]})
    return results


def ingest_event(conn, event: SampleEvent):
    if event.provider == "stripe":
        return _ingest_stripe_event(conn, event)
    if event.provider == "shopify":
        return _ingest_shopify_event(conn, event)
    raise ValueError(f"unsupported provider: {event.provider}")


def _ingest_stripe_event(conn, event: SampleEvent):
    payload = event.payload
    existing = store.find_first_non_duplicate(conn, event.event_id)
    if existing is not None:
        return store.insert_event(
            conn,
            provider=event.provider,
            event_id=event.event_id,
            event_type=event.event_type,
            status="duplicate",
            payload=payload,
            failure_reason="Duplicate event ID already processed; credit grant skipped.",
            duplicate_of_event_id=event.event_id,
            credit_delta=0,
            suggested_fix="Keep event-id idempotency keys before applying account credits.",
        )

    duplicate_object = _find_duplicate_stripe_object_event(conn, event)
    if duplicate_object is not None:
        object_id = _stripe_object_id(payload)
        return store.insert_event(
            conn,
            provider=event.provider,
            event_id=event.event_id,
            event_type=event.event_type,
            status="duplicate_object",
            payload=payload,
            failure_reason=(
                "Duplicate Stripe object event already processed for "
                f"{event.event_type} object {object_id}; credit grant skipped."
            ),
            duplicate_of_event_id=duplicate_object["event_id"],
            credit_delta=0,
            suggested_fix=(
                "Use provider, event type, and Stripe object ID as a second idempotency guard "
                "before applying customer credits."
            ),
        )

    if event.event_type == "subscription.status_check":
        customer_id = payload["customer_id"]
        local_status = payload["local_subscription_status"]
        provider_status = payload["provider_subscription_status"]
        status = "desync" if local_status != provider_status else "accepted"
        failure_reason = None
        suggested_fix = None
        if status == "desync":
            failure_reason = (
                f"Local subscription is {local_status}; provider subscription is {provider_status}."
            )
            suggested_fix = "Replay missed subscription webhook or run a reconciliation job."
        store.upsert_account(
            conn,
            customer_id=customer_id,
            subscription_status_local=local_status,
            subscription_status_provider=provider_status,
        )
        return store.insert_event(
            conn,
            provider=event.provider,
            event_id=event.event_id,
            event_type=event.event_type,
            status=status,
            payload=payload,
            failure_reason=failure_reason,
            suggested_fix=suggested_fix,
        )

    credit_delta = 0
    if event.event_type in STRIPE_CREDIT_TYPES and event.expected_outcome == "accepted":
        credit_delta = int(payload.get("credits", 100))
        store.upsert_account(
            conn,
            customer_id=payload["customer_id"],
            credit_delta=credit_delta,
        )

    return store.insert_event(
        conn,
        provider=event.provider,
        event_id=event.event_id,
        event_type=event.event_type,
        status=event.expected_outcome,
        payload=payload,
        failure_reason=event.failure_reason,
        credit_delta=credit_delta,
    )


def _find_duplicate_stripe_object_event(conn, event: SampleEvent):
    object_id = _stripe_object_id(event.payload)
    if object_id is None:
        return None

    for row in store.list_events(conn):
        if row["provider"] != "stripe":
            continue
        if row["event_type"] != event.event_type:
            continue
        if row["status"] in {"duplicate", "duplicate_object"}:
            continue
        existing_payload = store.decode_payload(row)
        if _stripe_object_id(existing_payload) == object_id:
            return row
    return None


def _stripe_object_id(payload: dict[str, Any]) -> str | None:
    for key in (
        "invoice_id",
        "payment_intent_id",
        "checkout_session_id",
        "subscription_id",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    data = payload.get("data")
    if isinstance(data, dict):
        obj = data.get("object")
        if isinstance(obj, dict):
            value = obj.get("id")
            if isinstance(value, str) and value:
                return value
    return None


def _ingest_shopify_event(conn, event: SampleEvent):
    suggested_fix = None
    if event.expected_outcome == "replay_pending":
        if event.failure_reason == "missing required order email":
            suggested_fix = "Make handler tolerate nullable customer/email fields and replay safely."
        elif event.failure_reason == "handler timeout":
            suggested_fix = "Move slow fulfillment work behind a queue and replay the stored payload."
        else:
            suggested_fix = "Review handler validation and replay after the fix."

    return store.insert_event(
        conn,
        provider=event.provider,
        event_id=event.event_id,
        event_type=event.event_type,
        status=event.expected_outcome,
        payload=event.payload,
        failure_reason=event.failure_reason,
        suggested_fix=suggested_fix,
    )
