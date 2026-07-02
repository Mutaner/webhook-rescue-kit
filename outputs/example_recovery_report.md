# Stripe Duplicate Credit Guard Diagnostic

## Executive Summary
- Events processed: 7
- Stripe duplicate credit findings: 2
- Failed events captured: 2
- Replayed events: 1
- Subscription desync findings: 1

## Stripe Duplicate Credit Findings
- Duplicate Stripe Event ID: `evt_test_invoice_001_a` was detected as a duplicate of `evt_test_invoice_001_a`; credit grant was skipped to prevent double counting.
- Duplicate Stripe Object Event: `evt_test_invoice_001_b` was detected as a duplicate of `evt_test_invoice_001_a`; credit grant was skipped to prevent double counting.

## Account Credit State
- `cus_credit_demo_001` has 100 credits; local subscription `unknown`, provider subscription `unknown`.
- `cus_desync_demo_001` has 0 credits; local subscription `inactive`, provider subscription `active`.

## Shopify Failed Order Recovery
- `shopify_order_failed_missing_field` `orders/create` captured as `replayed`: missing required order email.
- `shopify_order_failed_timeout` `orders/create` captured as `replay_pending`: handler timeout.

## Shopify Replay Candidates
- `shopify_order_failed_timeout` can be replayed locally after handler fixes.

## Simulated Replayed Events
- `shopify_order_failed_missing_field` replayed at `2026-07-02T18:27:43+00:00`: simulated local replay succeeded; no external API was called.

## Subscription Desync Findings
- `sub_desync_001`: Local subscription is inactive; provider subscription is active.

## Events Processed
- `evt_test_invoice_001_a` `stripe` `invoice.paid` -> `accepted`
- `evt_test_invoice_001_a` `stripe` `invoice.paid` -> `duplicate`
- `evt_test_invoice_001_b` `stripe` `invoice.paid` -> `duplicate_object`
- `shopify_order_ok_001` `shopify` `orders/create` -> `accepted`
- `shopify_order_failed_missing_field` `shopify` `orders/create` -> `replayed`
- `shopify_order_failed_timeout` `shopify` `orders/create` -> `replay_pending`
- `sub_desync_001` `stripe` `subscription.status_check` -> `desync`

## What I would check in your repo
- Where Stripe `invoice.paid` or checkout success handlers grant account credits.
- Whether event ID idempotency is stored before the credit side effect runs.
- Whether a second guard exists for Stripe object IDs such as invoice, payment intent, checkout session, or subscription IDs.
- Whether duplicate deliveries return a safe success response without reapplying credits.
- Whether failed order payloads are retained with enough context for reviewed local replay.

## Acceptance criteria
- Replaying the same Stripe event ID does not increase credits twice.
- Receiving a different Stripe event ID for the same invoice/payment object does not increase credits twice.
- The credit demo customer remains separate from the subscription desync demo customer.
- Replay remains simulated locally and performs no external API calls.
- The generated report names duplicate Stripe object events clearly.

## Recommended Fixes
- `evt_test_invoice_001_a`: Keep event-id idempotency keys before applying account credits.
- `evt_test_invoice_001_b`: Use provider, event type, and Stripe object ID as a second idempotency guard before applying customer credits.
- `shopify_order_failed_missing_field`: Make handler tolerate nullable customer/email fields and replay safely.
- `shopify_order_failed_timeout`: Move slow fulfillment work behind a queue and replay the stored payload.
- `sub_desync_001`: Replay missed subscription webhook or run a reconciliation job.
- Persist provider event IDs before side effects.
- Store failed payloads with failure reasons for replay.
- Run periodic subscription reconciliation against provider state snapshots.

## No-Live-API / No-Secrets Safety Boundary
- This is a local proof asset using synthetic data only.
- No real Stripe or Shopify APIs are called.
- No API keys, webhook signing secrets, customer data, or provider credentials are required.
- No production authentication, signing verification, queueing, or alerting is included.
- Replay is simulated locally and should be replaced with reviewed production-safe logic.
