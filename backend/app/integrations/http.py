import logging
import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol, cast

import httpx2

from app.integrations.errors import (
    UpstreamNotFoundError,
    UpstreamRateLimitError,
    UpstreamResponseError,
    UpstreamUnavailableError,
)

logger = logging.getLogger(__name__)


class JsonHttpClient(Protocol):
    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        not_found_message: str,
    ) -> dict[str, Any]: ...


class TextHttpClient(JsonHttpClient, Protocol):
    def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        not_found_message: str,
    ) -> str: ...


class RetryingJsonClient:
    """Synchronous JSON transport with bounded retries for read-only provider calls."""

    def __init__(
        self,
        client: httpx2.Client,
        *,
        provider: str,
        max_attempts: int,
        backoff_seconds: float,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.client = client
        self.provider = provider
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleeper = sleeper

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        not_found_message: str,
    ) -> dict[str, Any]:
        response = self._get_response(url, params=params, not_found_message=not_found_message)
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamResponseError(
                self.provider, f"{self.provider} returned malformed JSON."
            ) from exc
        if not isinstance(payload, dict):
            raise UpstreamResponseError(
                self.provider, f"{self.provider} returned an unexpected response shape."
            )
        return cast(dict[str, Any], payload)

    def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None = None,
        not_found_message: str,
    ) -> str:
        return self._get_response(url, params=params, not_found_message=not_found_message).text

    def _get_response(
        self,
        url: str,
        *,
        params: Mapping[str, str | int] | None,
        not_found_message: str,
    ) -> httpx2.Response:
        for attempt in range(1, self.max_attempts + 1):
            try:
                with self.client.stream("GET", url, params=params) as streamed:
                    body = bytearray()
                    for chunk in streamed.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 2_000_000:
                            raise UpstreamResponseError(
                                self.provider, "Provider response exceeds the single-record limit."
                            )
                    response = httpx2.Response(
                        streamed.status_code,
                        headers={
                            key: value
                            for key, value in streamed.headers.items()
                            if key not in {"content-encoding", "content-length"}
                        },
                        content=bytes(body),
                        request=streamed.request,
                    )
            except (httpx2.TimeoutException, httpx2.TransportError) as exc:
                if attempt == self.max_attempts:
                    raise UpstreamUnavailableError(
                        self.provider,
                        f"{self.provider} could not be reached after {attempt} attempts.",
                    ) from exc
                self._wait(attempt, None, reason=type(exc).__name__)
                continue

            if response.status_code == 404:
                raise UpstreamNotFoundError(self.provider, not_found_message)

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == self.max_attempts:
                    error_type = (
                        UpstreamRateLimitError
                        if response.status_code == 429
                        else UpstreamUnavailableError
                    )
                    message = (
                        f"{self.provider} rate limit was reached; retry later."
                        if response.status_code == 429
                        else f"{self.provider} is temporarily unavailable."
                    )
                    raise error_type(self.provider, message)
                self._wait(
                    attempt,
                    response.headers.get("Retry-After"),
                    reason=f"HTTP {response.status_code}",
                )
                continue

            if response.is_error:
                raise UpstreamResponseError(
                    self.provider,
                    f"{self.provider} rejected the request with HTTP {response.status_code}.",
                )

            return response

        raise AssertionError("Retry loop exited without returning or raising.")

    def _wait(self, attempt: int, retry_after: str | None, *, reason: str) -> None:
        delay = self._retry_after_seconds(retry_after)
        if delay is None:
            delay = self.backoff_seconds * (2 ** (attempt - 1))
        delay = min(delay, 60.0)
        logger.warning(
            "%s request failed (%s); retrying attempt %d/%d in %.2fs",
            self.provider,
            reason,
            attempt + 1,
            self.max_attempts,
            delay,
        )
        self.sleeper(delay)

    @staticmethod
    def _retry_after_seconds(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None
