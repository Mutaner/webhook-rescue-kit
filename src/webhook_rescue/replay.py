from __future__ import annotations

from pathlib import Path

from webhook_rescue import store


def replay_event(db_path: Path, event_id: str) -> dict[str, str]:
    store.init_db(db_path)
    with store.connect(db_path) as conn:
        row = store.get_latest_event(conn, event_id)
        if row["status"] not in {"replay_pending", "failed"}:
            return {
                "event_id": event_id,
                "status": row["status"],
                "replay_result": "not replayed; event is not pending replay",
            }

        result = "simulated local replay succeeded; no external API was called"
        conn.execute(
            """
            UPDATE events
            SET status = 'replayed', replay_result = ?, replayed_at = ?
            WHERE id = ?
            """,
            (result, store.utc_now(), row["id"]),
        )
        updated = store.get_latest_event(conn, event_id)
        return {
            "event_id": event_id,
            "status": updated["status"],
            "replay_result": updated["replay_result"],
        }

