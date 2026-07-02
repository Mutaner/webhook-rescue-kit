from __future__ import annotations

from pathlib import Path

from webhook_rescue import store
from webhook_rescue.utils import ensure_parent


def generate_report(db_path: Path, output_path: Path) -> str:
    store.init_db(db_path)
    with store.connect(db_path) as conn:
        events = store.list_events(conn)
        accounts = store.list_accounts(conn)

    duplicates = [row for row in events if row["status"] in {"duplicate", "duplicate_object"}]
    stripe_duplicate_credit_findings = [
        row
        for row in duplicates
        if row["provider"] == "stripe"
        and row["event_type"] in {"invoice.paid", "checkout.session.completed"}
    ]
    failed = [
        row
        for row in events
        if row["provider"] == "shopify" and row["failure_reason"]
    ]
    replay_candidates = [row for row in events if row["status"] in {"replay_pending", "failed"}]
    replayed = [row for row in events if row["status"] == "replayed"]
    desyncs = [row for row in events if row["status"] == "desync"]

    lines: list[str] = [
        "# Stripe Duplicate Credit Guard Diagnostic",
        "",
        "## Executive Summary",
        f"- Events processed: {len(events)}",
        f"- Stripe duplicate credit findings: {len(stripe_duplicate_credit_findings)}",
        f"- Failed events captured: {len(failed)}",
        f"- Replayed events: {len(replayed)}",
        f"- Subscription desync findings: {len(desyncs)}",
        "",
        "## Stripe Duplicate Credit Findings",
    ]
    if stripe_duplicate_credit_findings:
        for row in stripe_duplicate_credit_findings:
            label = (
                "Duplicate Stripe Object Event"
                if row["status"] == "duplicate_object"
                else "Duplicate Stripe Event ID"
            )
            lines.append(
                f"- {label}: `{row['event_id']}` was detected as a duplicate of "
                f"`{row['duplicate_of_event_id']}`; credit grant was skipped to prevent double counting."
            )
    else:
        lines.append("- None detected.")

    lines.extend(["", "## Account Credit State"])
    if accounts:
        for row in accounts:
            lines.append(
                f"- `{row['customer_id']}` has {row['credits']} credits; "
                f"local subscription `{row['subscription_status_local'] or 'unknown'}`, "
                f"provider subscription `{row['subscription_status_provider'] or 'unknown'}`."
            )
    else:
        lines.append("- No accounts recorded.")

    lines.extend(["", "## Shopify Failed Order Recovery"])
    if failed:
        for row in failed:
            lines.append(
                f"- `{row['event_id']}` `{row['event_type']}` captured as `{row['status']}`: "
                f"{row['failure_reason'] or 'no reason recorded'}."
            )
    else:
        lines.append("- No failed webhook payloads captured.")

    lines.extend(["", "## Shopify Replay Candidates"])
    if replay_candidates:
        for row in replay_candidates:
            lines.append(f"- `{row['event_id']}` can be replayed locally after handler fixes.")
    else:
        lines.append("- None currently pending.")

    lines.extend(["", "## Simulated Replayed Events"])
    if replayed:
        for row in replayed:
            lines.append(
                f"- `{row['event_id']}` replayed at `{row['replayed_at']}`: {row['replay_result']}."
            )
    else:
        lines.append("- None replayed yet.")

    lines.extend(["", "## Subscription Desync Findings"])
    if desyncs:
        for row in desyncs:
            lines.append(f"- `{row['event_id']}`: {row['failure_reason']}")
    else:
        lines.append("- No subscription state mismatches detected.")

    lines.extend(["", "## Events Processed"])
    lines.extend(_event_lines(events))

    lines.extend(["", "## What I would check in your repo"])
    lines.extend(
        [
            "- Where Stripe `invoice.paid` or checkout success handlers grant account credits.",
            "- Whether event ID idempotency is stored before the credit side effect runs.",
            "- Whether a second guard exists for Stripe object IDs such as invoice, payment intent, checkout session, or subscription IDs.",
            "- Whether duplicate deliveries return a safe success response without reapplying credits.",
            "- Whether failed order payloads are retained with enough context for reviewed local replay.",
        ]
    )

    lines.extend(["", "## Acceptance criteria"])
    lines.extend(
        [
            "- Replaying the same Stripe event ID does not increase credits twice.",
            "- Receiving a different Stripe event ID for the same invoice/payment object does not increase credits twice.",
            "- The credit demo customer remains separate from the subscription desync demo customer.",
            "- Replay remains simulated locally and performs no external API calls.",
            "- The generated report names duplicate Stripe object events clearly.",
        ]
    )

    lines.extend(["", "## Recommended Fixes"])
    fixes = [row for row in events if row["suggested_fix"]]
    if fixes:
        for row in fixes:
            lines.append(f"- `{row['event_id']}`: {row['suggested_fix']}")
    else:
        lines.append("- No specific fixes recorded.")
    lines.extend(
        [
            "- Persist provider event IDs before side effects.",
            "- Store failed payloads with failure reasons for replay.",
            "- Run periodic subscription reconciliation against provider state snapshots.",
            "",
            "## No-Live-API / No-Secrets Safety Boundary",
            "- This is a local proof asset using synthetic data only.",
            "- No real Stripe or Shopify APIs are called.",
            "- No API keys, webhook signing secrets, customer data, or provider credentials are required.",
            "- No production authentication, signing verification, queueing, or alerting is included.",
            "- Replay is simulated locally and should be replaced with reviewed production-safe logic.",
            "",
        ]
    )

    markdown = "\n".join(lines)
    ensure_parent(output_path)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


def _event_lines(events) -> list[str]:
    if not events:
        return ["- No events processed."]
    return [
        f"- `{row['event_id']}` `{row['provider']}` `{row['event_type']}` -> `{row['status']}`"
        for row in events
    ]
