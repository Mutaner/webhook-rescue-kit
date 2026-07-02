from __future__ import annotations

from pathlib import Path

from webhook_rescue import store
from webhook_rescue.utils import ensure_parent


def generate_report(db_path: Path, output_path: Path) -> str:
    store.init_db(db_path)
    with store.connect(db_path) as conn:
        events = store.list_events(conn)
        accounts = store.list_accounts(conn)

    duplicates = [row for row in events if row["status"] == "duplicate"]
    failed = [
        row
        for row in events
        if row["provider"] == "shopify" and row["failure_reason"]
    ]
    replay_candidates = [row for row in events if row["status"] in {"replay_pending", "failed"}]
    replayed = [row for row in events if row["status"] == "replayed"]
    desyncs = [row for row in events if row["status"] == "desync"]

    lines: list[str] = [
        "# Webhook Recovery Report",
        "",
        "## Executive Summary",
        f"- Events processed: {len(events)}",
        f"- Duplicate events detected: {len(duplicates)}",
        f"- Failed events captured: {len(failed)}",
        f"- Replayed events: {len(replayed)}",
        f"- Subscription desync findings: {len(desyncs)}",
        "",
        "## Events Processed",
    ]
    lines.extend(_event_lines(events))

    lines.extend(["", "## Duplicate Events Detected"])
    if duplicates:
        for row in duplicates:
            lines.append(
                f"- `{row['event_id']}` was detected as a duplicate of `{row['duplicate_of_event_id']}`; "
                "credit grant was skipped to prevent double counting."
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

    lines.extend(["", "## Failed Events Captured"])
    if failed:
        for row in failed:
            lines.append(
                f"- `{row['event_id']}` `{row['event_type']}` captured as `{row['status']}`: "
                f"{row['failure_reason'] or 'no reason recorded'}."
            )
    else:
        lines.append("- No failed webhook payloads captured.")

    lines.extend(["", "## Replay Candidates"])
    if replay_candidates:
        for row in replay_candidates:
            lines.append(f"- `{row['event_id']}` can be replayed locally after handler fixes.")
    else:
        lines.append("- None currently pending.")

    lines.extend(["", "## Replayed Events"])
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
            "## Limitations",
            "- This is a local proof asset using synthetic data only.",
            "- No real Stripe or Shopify APIs are called.",
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
