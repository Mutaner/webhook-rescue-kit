# webhook-rescue-kit

`webhook-rescue-kit` is a local Python CLI proof asset for a fixed-scope service: **Stripe / Shopify Webhook Failure Recovery Pilot**.

It demonstrates how a small recovery workflow can detect duplicate provider events, store failed webhook payloads, mark replay candidates, simulate safe local replay, identify subscription state drift, and generate a Markdown recovery report.

This repository uses only synthetic sample data. It does not use real API keys, call Stripe or Shopify APIs, process customer data, or claim production readiness.

## For Technical Founders

If your Stripe or Shopify webhooks are failing, duplicating events, or causing subscription/order state drift, this repo shows the kind of fixed-scope recovery artifact I can build:

- idempotency check;
- failed-event inventory;
- replay/reconciliation script;
- Markdown recovery report;
- implementation notes.

This is not a SaaS product. It is a proof-of-work repo for a small paid pilot.

## Paid Pilot Scope

A focused paid pilot covers one webhook flow, for example:

- Stripe `invoice.paid`;
- Stripe `customer.subscription.updated`;
- Shopify `orders/create`;
- Shopify `orders/updated`.

Deliverables usually include idempotency review, failed-event capture, replay/reconciliation tooling, tests where practical, rollback notes, and a short recovery report.

See [`docs/paid-pilot.md`](docs/paid-pilot.md) for the full scope and boundaries.

## Demo Report Preview

The demo generates a recovery-style report showing:

```text
Total events
Stripe duplicate credit findings
Failed events
Replay candidates
Recommended fixes
```

## Buyer Pain This Targets

Webhook failures often show up as billing credits applied twice, Shopify orders not reaching internal systems, missed subscription updates, and unclear retry history. A buyer with those problems usually needs a focused audit and a small recovery path before committing to larger reliability work.

This demo shows the shape of that work without touching any live platform.

## What The CLI Demonstrates

- Stripe duplicate event idempotency with `evt_test_invoice_001_a`.
- Stripe object-level idempotency with `evt_test_invoice_001_b` for `invoice_demo_001`.
- Prevention of double credit counting for paid invoice events.
- Shopify `orders/create` failed-event capture.
- A persisted replay queue using SQLite.
- Local simulated replay for failed events.
- Subscription state desync detection.
- A Markdown recovery report generated from SQLite state.

## Install

Requires Python 3.11+.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Run The Demo

```bash
webhook-rescue demo
```

The demo resets `.webhook_rescue/webhook_rescue.db`, ingests all sample files, replays one failed Shopify event, and writes:

```text
outputs/recovery_report.md
```

A committed example report is available at:

```text
outputs/example_recovery_report.md
```

## Example Commands

```bash
webhook-rescue init
webhook-rescue ingest --file samples/stripe_duplicate_events.json
webhook-rescue ingest --file samples/shopify_failed_orders.json
webhook-rescue ingest --file samples/subscription_desync.json
webhook-rescue inspect --event-id evt_test_invoice_001_b
webhook-rescue replay --event-id shopify_order_failed_timeout
webhook-rescue report --output outputs/recovery_report.md
```

All commands use SQLite state. Tests pass temporary database paths with `--db` equivalents internally and do not depend on the default demo database.

## Example Output

Inspecting the Stripe object duplicate scenario after demo shows account credits of `100`, even though the sample contains two different Stripe event IDs for the same invoice object:

```text
Event evt_test_invoice_001_b
provider: stripe
type: invoice.paid
status: duplicate_object
failure_reason: Duplicate Stripe object event already processed for invoice.paid object invoice_demo_001; credit grant skipped.
account: cus_credit_demo_001 credits=100 local_subscription=unknown provider_subscription=unknown
```

The report includes sections for Stripe duplicate credit findings, account credit state, Shopify failed order recovery, replay candidates, replayed events, subscription desync findings, acceptance criteria, recommended fixes, and the no-live-API/no-secrets safety boundary.

## Safety Notes

- Uses synthetic sample payloads only.
- Does not call real Stripe, Shopify, or other external APIs.
- Does not require API keys or secrets.
- Stores local SQLite files only.
- Replay is simulated locally and does not send network requests.

## What Is Not Included

- Production webhook signature verification.
- Real provider API integration.
- Real queue workers or background jobs.
- Alerting, dashboards, or incident management.
- Multi-tenant access controls.
- A complete production replay safety review.

## Paid Pilot This Demonstrates

### Stripe / Shopify Webhook Failure Recovery Pilot

Fixed-scope deliverables:

- webhook failure audit;
- idempotency check;
- failed-event capture design;
- replay/reconciliation script;
- markdown recovery report;
- implementation notes.

This proof asset maps to a paid pilot by showing the concrete artifacts a buyer would receive: a failure inventory, idempotency findings, replay candidates, reconciliation notes, and a concise recovery report. The production version would be scoped against the buyer's real systems, reviewed for platform terms and security requirements, and implemented without relying on this demo's synthetic shortcuts.

## Tests

```bash
python -m pytest
```

The test suite verifies persisted SQLite behavior for duplicate detection, credit double-count prevention, failed-event storage, replay updates, desync detection, and report generation.
