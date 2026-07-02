from __future__ import annotations

import json
from typing import Annotated
from pathlib import Path

import typer

from webhook_rescue import demo as demo_module
from webhook_rescue import ingest as ingest_module
from webhook_rescue import replay as replay_module
from webhook_rescue import report as report_module
from webhook_rescue import store
from webhook_rescue.utils import DEFAULT_DB_PATH, DEFAULT_REPORT_PATH


app = typer.Typer(help="Local webhook failure recovery proof asset.")

DbOption = Annotated[
    Path,
    typer.Option("--db", help="SQLite database path."),
]
EventIdOption = Annotated[str, typer.Option("--event-id", help="Provider event ID.")]
SampleFileOption = Annotated[
    Path,
    typer.Option("--file", "-f", help="Sample JSON file to ingest."),
]
ReportOutputOption = Annotated[
    Path,
    typer.Option("--output", "-o", help="Markdown report output path."),
]


@app.command()
def init(db: DbOption = DEFAULT_DB_PATH) -> None:
    """Create the local SQLite database."""
    store.init_db(db)
    Path("outputs").mkdir(parents=True, exist_ok=True)
    typer.echo(f"Initialized local database at {db}")


@app.command()
def ingest(file: SampleFileOption, db: DbOption = DEFAULT_DB_PATH) -> None:
    """Load synthetic events into SQLite."""
    for result in ingest_module.ingest_file(db, file):
        typer.echo(f"{result['event_id']}: {result['status']}")


@app.command()
def inspect(event_id: EventIdOption, db: DbOption = DEFAULT_DB_PATH) -> None:
    """Show one event and related account state."""
    _inspect(db, event_id)


@app.command()
def replay(event_id: EventIdOption, db: DbOption = DEFAULT_DB_PATH) -> None:
    """Replay a pending event locally."""
    result = replay_module.replay_event(db, event_id)
    typer.echo(f"{result['event_id']}: {result['status']} ({result['replay_result']})")


@app.command()
def report(
    output: ReportOutputOption = DEFAULT_REPORT_PATH,
    db: DbOption = DEFAULT_DB_PATH,
) -> None:
    """Generate a Markdown report from SQLite."""
    report_module.generate_report(db, output)
    typer.echo(f"Generated report at {output}")


@app.command()
def demo(
    output: ReportOutputOption = DEFAULT_REPORT_PATH,
    db: DbOption = DEFAULT_DB_PATH,
) -> None:
    """Run the complete local demo."""
    result = demo_module.run_demo(db, output)
    typer.echo(f"Demo database: {result['db']}")
    typer.echo(f"Demo report: {result['report']}")


def _inspect(db: Path, event_id: str) -> None:
    store.init_db(db)
    with store.connect(db) as conn:
        row = store.get_latest_event(conn, event_id)
        payload = json.loads(row["payload_json"])
        typer.echo(f"Event {row['event_id']}")
        typer.echo(f"provider: {row['provider']}")
        typer.echo(f"type: {row['event_type']}")
        typer.echo(f"status: {row['status']}")
        if row["failure_reason"]:
            typer.echo(f"failure_reason: {row['failure_reason']}")
        if row["replay_result"]:
            typer.echo(f"replay_result: {row['replay_result']}")
        if row["credit_delta"]:
            typer.echo(f"credit_delta: {row['credit_delta']}")
        customer_id = payload.get("customer_id")
        if customer_id:
            account = store.get_account(conn, customer_id)
            if account:
                typer.echo(
                    "account: "
                    f"{account['customer_id']} credits={account['credits']} "
                    f"local_subscription={account['subscription_status_local'] or 'unknown'} "
                    f"provider_subscription={account['subscription_status_provider'] or 'unknown'}"
                )


if __name__ == "__main__":
    app()
