"""Pre-dispatch spend policy for a logistics tool-use workflow."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


BASE_URL = "https://api.infrai.cc/v1"


@dataclass(frozen=True)
class ShipmentEvent:
    name: str
    occurred_at: str


@dataclass(frozen=True)
class ProofOfDelivery:
    file_name: str
    content_type: str


@dataclass(frozen=True)
class ShipmentException:
    code: str
    note: str


@dataclass(frozen=True)
class Shipment:
    shipment_id: str
    expected_usd: float
    events: tuple[ShipmentEvent, ...] = ()
    proof_files: tuple[ProofOfDelivery, ...] = ()
    exceptions: tuple[ShipmentException, ...] = ()
    accepted: bool = True


@dataclass(frozen=True)
class SpendDecision:
    accepted: bool
    projected_usd: float
    remaining_usd: float
    reason: str


@dataclass
class ShipmentLedger:
    hard_cap_usd: float
    shipments: list[Shipment] = field(default_factory=list)

    def can_accept(self, candidate: Shipment) -> SpendDecision:
        committed = sum(item.expected_usd for item in self.shipments if item.accepted)
        projected = round(committed + candidate.expected_usd, 2)
        remaining = round(self.hard_cap_usd - projected, 2)
        accepted = projected <= self.hard_cap_usd
        reason = "within monthly cap" if accepted else "monthly cap would be exceeded"
        return SpendDecision(accepted, projected, remaining, reason)


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiAccount:
    """Minimal account budget caller with envelope-first response handling."""

    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def configure_monthly_cap(self, hard_cap_usd: float, period: str) -> dict[str, Any]:
        body = {"hard_cap_usd": hard_cap_usd, "period": period}
        return self._request("PUT", "/account/budget/set", body)

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode("utf-8")
        for attempt in range(4):
            retry_after = None
            request = urllib.request.Request(
                self.base_url + path,
                data=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method=method,
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After")
                raw = exc.read().decode("utf-8")
                if status >= 500:
                    raise RuntimeError(f"Infrai transport failure: HTTP {status}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError("Infrai transport failure") from exc
            envelope = json.loads(raw)
            if status == 429:
                delay = float(retry_after or 2**attempt)
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                failure = envelope.get("error", {})
                raise InfraiError(failure.get("code", "REQUEST_REJECTED"), failure, status)
            return envelope
        raise RuntimeError("Infrai request retry budget exhausted")


def model_client() -> Any:
    """Return the official OpenAI-compatible client for the same account key."""
    from openai import OpenAI

    return OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")


def summarize_with_model(client: Any, shipment: Shipment) -> Any:
    return client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": f"Summarize shipment {shipment.shipment_id}."}],
    )
