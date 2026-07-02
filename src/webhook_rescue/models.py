from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Provider = Literal["stripe", "shopify"]


@dataclass(frozen=True)
class SampleEvent:
    provider: Provider
    event_id: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = "accepted"
    failure_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SampleEvent":
        provider = data["provider"]
        if provider not in {"stripe", "shopify"}:
            raise ValueError(f"unsupported provider: {provider}")
        return cls(
            provider=provider,
            event_id=data["event_id"],
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            expected_outcome=data.get("expected_outcome", "accepted"),
            failure_reason=data.get("failure_reason"),
        )
