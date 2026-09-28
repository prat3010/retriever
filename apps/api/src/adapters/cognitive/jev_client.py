"""TypeSafe AI Jev Decision Engine Client (Battery #42).

Provides an asynchronous HTTP client for TypeSafe AI's Jev model,
enabling non-autoregressive, sub-100ms structured decision evaluation
with in-process circuit breaker resilience and tenant isolation.
"""

import logging
import time
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger("api")


class JevCircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class JevClient:
    """Client for evaluating non-autoregressive typed decisions via TypeSafe AI Jev."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.typesafe.ai/v1",
        timeout_sec: float = 0.5,
        failure_threshold: int = 3,
        recovery_timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        # Circuit breaker state
        self._circuit_state: JevCircuitState = JevCircuitState.CLOSED
        self._consecutive_failures: int = 0
        self._last_failure_timestamp: float = 0.0
        self._ewma_latency_ms: float = 0.0

    @property
    def circuit_state(self) -> JevCircuitState:
        now = time.monotonic()
        if (
            self._circuit_state == JevCircuitState.OPEN
            and (now - self._last_failure_timestamp) > self.recovery_timeout
        ):
            self._circuit_state = JevCircuitState.HALF_OPEN
        return self._circuit_state

    @property
    def is_available(self) -> bool:
        if not self.api_key:
            return False
        return self.circuit_state != JevCircuitState.OPEN

    @property
    def ewma_latency_ms(self) -> float:
        return self._ewma_latency_ms

    def _record_success(self, duration_ms: float) -> None:
        self._circuit_state = JevCircuitState.CLOSED
        self._consecutive_failures = 0
        if self._ewma_latency_ms == 0.0:
            self._ewma_latency_ms = duration_ms
        else:
            self._ewma_latency_ms = (0.2 * duration_ms) + (0.8 * self._ewma_latency_ms)

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        self._last_failure_timestamp = time.monotonic()
        if self._consecutive_failures >= self.failure_threshold:
            self._circuit_state = JevCircuitState.OPEN
            logger.warning(
                "JevClient circuit breaker tripped to OPEN after %d consecutive failures",
                self._consecutive_failures,
            )

    async def decide(
        self,
        state: str,
        questions: dict[str, Any],
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute non-autoregressive typed evaluation against Jev decision endpoint.

        Args:
            state: Unstructured input context (e.g., user query or retrieved context).
            questions: Dictionary defining question schemas, types, and allowed enums.
            tenant_id: Multi-tenant scoping identifier.

        Returns:
            Dictionary containing evaluated decisions with values and confidence probabilities.
        """
        if not self.api_key:
            raise ValueError("JEV_API_KEY is not configured; cannot invoke Jev engine")

        state_check = self.circuit_state
        if state_check == JevCircuitState.OPEN:
            raise RuntimeError(
                f"JevClient circuit breaker is OPEN (recovering after {self.recovery_timeout}s)"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if tenant_id:
            headers["X-Tenant-ID"] = tenant_id

        payload = {
            "state": state,
            "questions": questions,
        }

        start_time = time.monotonic()
        url = f"{self.base_url}/decide"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                self._record_failure()
                raise RuntimeError(
                    f"Jev API returned HTTP {response.status_code}: {response.text}"
                )

            data = response.json()
            duration_ms = (time.monotonic() - start_time) * 1000.0
            self._record_success(duration_ms)

            # Jev returns decisions keyed under "decisions" or root dict
            if isinstance(data, dict) and "decisions" in data:
                return data["decisions"]
            return data

        except (TimeoutError, httpx.RequestError) as err:
            self._record_failure()
            raise RuntimeError(f"JevClient network failure: {err}") from err
