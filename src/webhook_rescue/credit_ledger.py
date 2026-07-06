from __future__ import annotations

import hashlib
import json
from typing import Any


def classify_credit_webhook(existing_event, existing_credit, incoming) -> str:
    if _state(existing_event) == "credited":
        return "return_already_processed_no_credit_delta"

    if _state(existing_credit) == "credited":
        return "return_existing_credit_record_no_balance_increment"

    if _state(existing_event) == "in_flight":
        return "return_409_or_wait_for_original_processing"

    if _state(existing_event) == "failed_before_credit":
        return "safe_retry_same_event"

    return "claim_event_and_apply_credit_once"


def build_stripe_event_hash(stripe_event_id, event_type, livemode) -> str:
    return _stable_sha256(
        {
            "stripe_event_id": stripe_event_id,
            "event_type": event_type,
            "livemode": livemode,
        }
    )


def build_credit_operation_hash(
    workspace_id,
    stripe_payment_object_id,
    billing_reason,
    amount,
    currency,
    credit_type,
) -> str:
    return _stable_sha256(
        {
            "workspace_id": workspace_id,
            "stripe_payment_object_id": stripe_payment_object_id,
            "billing_reason": billing_reason,
            "amount": amount,
            "currency": currency,
            "credit_type": credit_type,
        }
    )


def _state(record) -> str | None:
    if record is None:
        return None
    if isinstance(record, dict):
        return record.get("state")
    return getattr(record, "state", None)


def _stable_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
