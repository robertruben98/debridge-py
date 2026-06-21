"""Exception hierarchy for the deBridge client."""

from __future__ import annotations

from typing import Optional


class DebridgeError(Exception):
    """Base class for all errors raised by this library.

    Catch this to handle any failure originating from ``debridge`` (currently
    just :class:`DebridgeAPIError`). Network-level failures from the underlying
    ``httpx`` client propagate as ``httpx`` exceptions and are not wrapped.
    """


class DebridgeAPIError(DebridgeError):
    """Raised when the deBridge API returns an error response.

    The DLN API signals errors with a JSON body of the shape
    ``{"errorCode", "errorId", "errorMessage", "reqId"}``. Crucially, errors are
    surfaced in **two** ways:

    * a non-2xx HTTP status (e.g. ``400 INVALID_QUERY_PARAMETERS`` /
      ``UNKNOWN_ORDER``), and
    * an HTTP **200** response whose body nonetheless carries an ``errorId``
      (e.g. ``COMPLIANCE_ADDRESS_BLOCKED``).

    The client detects both, so callers should rely on catching this exception
    rather than inspecting the HTTP status code themselves.

    Attributes:
        error_id: The API's ``errorId`` string (e.g. ``"UNKNOWN_ORDER"``), or
            ``None`` if the response carried no error id.
        error_code: The numeric ``errorCode``, or ``None``.
        message: The ``errorMessage`` text, falling back to ``"HTTP <status>"``.
        req_id: The API's ``reqId`` (useful for support tickets), or ``None``.
        status_code: The HTTP status code of the response (may be ``200``).

    Example::

        from debridge import DebridgeClient, DebridgeAPIError

        with DebridgeClient() as client:
            try:
                client.get_order_status("0xnot-an-order")
            except DebridgeAPIError as exc:
                print(exc.error_id, exc.status_code)  # 'UNKNOWN_ORDER' 400
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
