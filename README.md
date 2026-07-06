# webhook-rescue-kit

`webhook-rescue-kit` is a local Python CLI proof asset for **Stripe Duplicate Credit Guard**: duplicate-safe webhook side effects for credit grants and similar billing actions.

The main scenario is Stripe `invoice.paid` duplicate handling. The CLI demonstrates both same-event duplicate delivery and a different Stripe event ID pointing at the same invoice/payment object. In both cases, duplicate credit grants are skipped and recorded in a generated diagnostic report.

Shopify failed-order replay is included as a secondary example of failed webhook capture and local replay bookkeeping. It is not the primary offer or a full Shopify recovery system.

This repository uses synthetic sample data only. It does not use real API keys, call Stripe or Shopify APIs, process customer data, or claim production readiness.

## What The CLI Demonstrates

- Same Stripe event ID duplicate detection.
- Different Stripe event ID for the same invoice/payment object.
- Skipped duplicate credit grants before account credits are incremented.
- Failed Shopify order payload capture as a secondary replay example.
- Local simulated replay for failed events.
- Subscription state desync detection from synthetic provider snapshots.
- A generated Markdown diagnostic report.
- Tests covering idempotency, replay updates, desync detection, and report generation.

This is not a SaaS product, gateway, monitoring platform, or full webhook system. It is a small proof-of-work CLI that makes the duplicate-side-effect boundary easy to inspect.

## Safety Boundary

- Synthetic data only.
- No real Stripe or Shopify API calls.
- No secrets required.
- No production customer data.
- Local SQLite state only.
- Replay is simulated locally and does not send network requests.

## Credit Ledger Boundary

This repo models duplicate Stripe delivery as a credit-ledger idempotency problem. A webhook retry must not imply a new credit operation.

Event ID dedupe is useful, but the balance mutation should also be protected by a credit operation identity around the actual credit grant. See [docs/credit-ledger-boundary.md](docs/credit-ledger-boundary.md).

## Demo Report Preview

The demo generates `outputs/recovery_report.md`, with a committed example at `outputs/example_recovery_report.md`. The report includes:

- Stripe duplicate credit findings.
- Account credit state.
- Shopify failed order recovery.
- Replay candidates and simulated replay results.
- Subscription desync findings.
- Acceptance criteria.
- Recommended fixes.
- No-live-API/no-secrets safety boundary.

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

The demo resets `.webhook_rescue/webhook_rescue.db`, ingests all sample files, replays one failed Shopify event locally, and writes:

```text
outputs/recovery_report.md
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

## What Is Not Included

- Production webhook signature verification.
- Real provider API integration.
- Real queue workers or background jobs.
- Alerting, dashboards, or incident management.
- Multi-tenant access controls.
- A complete production replay safety review.

## Engineering Review Notes

The useful review surface is small: `samples/` defines synthetic provider events, `src/webhook_rescue/ingest.py` contains duplicate detection, `src/webhook_rescue/report.py` renders the diagnostic report, and `tests/` verifies the local behavior.

For commercial context, see `docs/paid-pilot.md`. That document is intentionally scoped as background, not a claim that this repository is deployable production infrastructure.

## Tests

```bash
python -m pytest
```

The test suite verifies persisted SQLite behavior for duplicate detection, credit double-count prevention, failed-event storage, replay updates, desync detection, and report generation.
