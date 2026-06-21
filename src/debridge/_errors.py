"""Exception hierarchy for the deBridge client."""

from __future__ import annotations

from typing import Optional


class DebridgeError(Exception):
    """Base class for all errors raised by this library."""


class DebridgeAPIError(DebridgeError):
    """Raised when the deBridge API returns an error response.

    The DLN API signals errors with a JSON body of the shape
    ``{"errorCode", "errorId", "errorMessage", "reqId"}``. Note that some
    errors (e.g. ``COMPLIANCE_ADDRESS_BLOCKED``) are returned with an HTTP 200
    status, so callers should rely on this exception rather than the status
    code alone.
    """

    def __init__(
        self,
        *,
        error_id: Optional[str],
        error_code: Optional[int],
        message: str,
        req_id: Optional[str],
        status_code: int,
    ) -> None:
        self.error_id = error_id
        self.error_code = error_code
        self.message = message
        self.req_id = req_id
        self.status_code = status_code
        label = error_id or f"HTTP {status_code}"
        super().__init__(f"[{label}] {message}")
