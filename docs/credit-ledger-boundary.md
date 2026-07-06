# Credit Ledger Idempotency Boundary

Invariant:

```text
webhook retry
does not imply
new credit operation
```

Stripe event ID dedupe is useful, but it is not enough by itself. A second Stripe delivery can use a different event ID while referring to the same invoice, payment intent, checkout session, or other payment object. The balance mutation needs its own idempotency boundary.

## Boundaries

1. Processed Stripe event identity: records whether a specific Stripe event delivery has already been claimed or completed.
2. Credit operation identity: protects the actual balance mutation using the workspace, payment object, billing reason, amount, currency, and credit type.

## States

- `in_flight`: the event was claimed and original processing has not finished.
- `credited`: the event or credit operation already completed the balance mutation.
- `failed_before_credit`: processing failed before changing the balance.
- `unknown`: no matching event or credit operation record exists.

## Acceptance Criteria

- Same event already credited => no balance change.
- Different event for same payment object already credited => no balance change.
- Event in flight => wait/conflict.
- Failed before credit => retry.
- First valid event => apply credit exactly once.

## Safety Note

This is a local reference only. It makes no real Stripe API calls, uses no secrets, and is not production-ready.
