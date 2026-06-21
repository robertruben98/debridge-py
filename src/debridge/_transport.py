"""Shared request-building and response/error-handling helpers.

These are VM-agnostic and used by both the sync and async clients so the
behaviour (query construction, error detection) is identical.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

import httpx

from debridge._errors import DebridgeAPIError


def normalize_base_url(base_url: str) -> str:
    """Strip a single trailing slash so path joins are predictable."""
    return base_url.rstrip("/")


def build_create_order_params(
    *,
    src_chain_id: int,
    src_chain_token_in: str,
    src_chain_token_in_amount: str,
    dst_chain_id: int,
    dst_chain_token_out: str,
    dst_chain_token_out_recipient: str,
    sender_address: str,
    dst_chain_token_out_amount: str = "auto",
    src_chain_order_authority_address: Optional[str] = None,
    dst_chain_order_authority_address: Optional[str] = None,
    referral_code: Optional[int] = None,
    affiliate_fee_percent: Optional[float] = None,
    affiliate_fee_recipient: Optional[str] = None,
    prepend_operating_expenses: Optional[bool] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Build the query params for ``GET /dln/order/create-tx``.

    The order authority addresses default to the sender (EVM) / recipient
    (Solana) when omitted, matching the deBridge dApp's behaviour: the source
    authority defaults to the sender, the destination authority to the
    recipient.
    """
    params: Dict[str, str] = {
        # int() unwraps IntEnum members (e.g. ChainId.BASE) so they render as
        # "8453" rather than "ChainId.BASE" (Python < 3.11 str() behaviour).
        "srcChainId": str(int(src_chain_id)),
        "srcChainTokenIn": src_chain_token_in,
        "srcChainTokenInAmount": src_chain_token_in_amount,
        "dstChainId": str(int(dst_chain_id)),
        "dstChainTokenOut": dst_chain_token_out,
        "dstChainTokenOutAmount": dst_chain_token_out_amount,
        "dstChainTokenOutRecipient": dst_chain_token_out_recipient,
        "senderAddress": sender_address,
        "srcChainOrderAuthorityAddress": src_chain_order_authority_address or sender_address,
        "dstChainOrderAuthorityAddress": dst_chain_order_authority_address
        or dst_chain_token_out_recipient,
    }
    if referral_code is not None:
        params["referralCode"] = str(int(referral_code))
    if affiliate_fee_percent is not None:
        params["affiliateFeePercent"] = str(affiliate_fee_percent)
    if affiliate_fee_recipient is not None:
        params["affiliateFeeRecipient"] = affiliate_fee_recipient
    if prepend_operating_expenses is not None:
        params["prependOperatingExpenses"] = str(prepend_operating_expenses).lower()
    if extra:
        params.update({k: str(v) for k, v in extra.items()})
    return params


def parse_response(response: httpx.Response) -> Dict[str, Any]:
    """Return the JSON body, raising ``DebridgeAPIError`` on any error.

    deBridge signals errors in two ways: a non-2xx status, OR an HTTP 200 body
    that nonetheless carries an ``errorId``/``errorCode`` (e.g. compliance
    blocks). Both are handled here.
    """
    data: Union[Dict[str, Any], Any]
    try:
        data = response.json()
    except ValueError:
        # Non-JSON body (e.g. an HTML 5xx page). Surface the status.
        if response.is_error:
            raise DebridgeAPIError(
                error_id=None,
                error_code=None,
                message=response.text or f"HTTP {response.status_code}",
                req_id=None,
                status_code=response.status_code,
            ) from None
        raise DebridgeAPIError(
            error_id=None,
            error_code=None,
            message="Response body was not valid JSON",
            req_id=None,
            status_code=response.status_code,
        ) from None

    # An error if the body carries an errorId (even on HTTP 200, e.g. compliance
    # blocks) OR the HTTP status itself is non-2xx.
    has_error_body = isinstance(data, dict) and "errorId" in data
    if has_error_body or response.is_error:
        body = data if isinstance(data, dict) else {}
        message = str(body.get("errorMessage") or "") or f"HTTP {response.status_code}"
        raise DebridgeAPIError(
            error_id=body.get("errorId"),
            error_code=body.get("errorCode"),
            message=message,
            req_id=body.get("reqId"),
            status_code=response.status_code,
        )

    if not isinstance(data, dict):
        raise DebridgeAPIError(
            error_id=None,
            error_code=None,
            message="Expected a JSON object response",
            req_id=None,
            status_code=response.status_code,
        )
    return data
