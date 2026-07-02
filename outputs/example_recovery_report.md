# Webhook Recovery Report

## Executive Summary
- Events processed: 6
- Duplicate events detected: 1
- Failed events captured: 2
- Replayed events: 1
- Subscription desync findings: 1

## Events Processed
- `evt_test_001` `stripe` `invoice.paid` -> `accepted`
- `evt_test_001` `stripe` `invoice.paid` -> `duplicate`
- `shopify_order_ok_001` `shopify` `orders/create` -> `accepted`
- `shopify_order_failed_missing_field` `shopify` `orders/create` -> `replayed`
- `shopify_order_failed_timeout` `shopify` `orders/create` -> `replay_pending`
- `sub_desync_001` `stripe` `subscription.status_check` -> `desync`

## Duplicate Events Detected
- `evt_test_001` was detected as a duplicate of `evt_test_001`; credit grant was skipped to prevent double counting.

## Account Credit State
- `cus_demo_001` has 100 credits; local subscription `inactive`, provider subscription `active`.

## Failed Events Captured
- `shopify_order_failed_missing_field` `orders/create` captured as `replayed`: missing required order email.
- `shopify_order_failed_timeout` `orders/create` captured as `replay_pending`: handler timeout.

## Replay Candidates
- `shopify_order_failed_timeout` can be replayed locally after handler fixes.

## Replayed Events
- `shopify_order_failed_missing_field` replayed at `2026-07-02T13:04:32+00:00`: simulated local replay succeeded; no external API was called.

## Subscription Desync Findings
- `sub_desync_001`: Local subscription is inactive; provider subscription is active.

## Recommended Fixes
- `evt_test_001`: Keep event-id idempotency keys before applying account credits.
- `shopify_order_failed_missing_field`: Make handler tolerate nullable customer/email fields and replay safely.
- `shopify_order_failed_timeout`: Move slow fulfillment work behind a queue and replay the stored payload.
- `sub_desync_001`: Replay missed subscription webhook or run a reconciliation job.
- Persist provider event IDs before side effects.
- Store failed payloads with failure reasons for replay.
- Run periodic subscription reconciliation against provider state snapshots.

## Limitations
- This is a local proof asset using synthetic data only.
- No real Stripe or Shopify APIs are called.
- No production authentication, signing verification, queueing, or alerting is included.
- Replay is simulated locally and should be replaced with reviewed production-safe logic.
