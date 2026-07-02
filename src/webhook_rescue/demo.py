from __future__ import annotations

from pathlib import Path

from webhook_rescue import ingest, replay, report, store
from webhook_rescue.utils import DEFAULT_DB_PATH, DEFAULT_REPORT_PATH


SAMPLE_FILES = [
    Path("samples/stripe_duplicate_events.json"),
    Path("samples/shopify_failed_orders.json"),
    Path("samples/subscription_desync.json"),
]


def run_demo(db_path: Path = DEFAULT_DB_PATH, report_path: Path = DEFAULT_REPORT_PATH) -> dict[str, str]:
    store.reset_db(db_path)
    for sample_file in SAMPLE_FILES:
        ingest.ingest_file(db_path, sample_file)
    replay.replay_event(db_path, "shopify_order_failed_missing_field")
    report.generate_report(db_path, report_path)
    return {
        "db": str(db_path),
        "report": str(report_path),
    }

