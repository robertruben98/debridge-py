"""Synchronous and asynchronous clients for the deBridge DLN API."""

from __future__ import annotations

import time
from types import TracebackType
from typing import Any, Dict, Optional, Type

import httpx

from debridge._transport import (
    build_create_order_params,
    normalize_base_url,
    parse_response,
)
from debridge.constants import DEFAULT_BASE_URL, TERMINAL_STATUSES
from debridge.models import (
    CreateOrderResponse,
    OrderDetails,
    OrderStatus,
    SupportedChainsResponse,
    TokenListResponse,
)


class _BaseClient:
    """Shared configuration for the sync/async clients."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self.base_url = normalize_base_url(base_url)


class DebridgeClient(_BaseClient):
    """Synchronous client for the deBridge DLN API.

    Example::

        with DebridgeClient() as client:
            chains = client.get_supported_chains()
            order = client.create_order(...)
            final = client.poll_status(order.order_id)
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(base_url)
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    # -- lifecycle --

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> DebridgeClient:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    # -- internal --

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self._client.get(f"{self.base_url}{path}", params=params)
        return parse_response(response)

    # -- endpoints --

    def get_supported_chains(self) -> SupportedChainsResponse:
        """``GET /supported-chains-info`` — chains the DLN currently supports."""
        return SupportedChainsResponse.model_validate(self._get("/supported-chains-info"))

    def get_token_list(self, chain_id: int) -> TokenListResponse:
        """``GET /token-list`` — tradable tokens for ``chain_id``."""
        return TokenListResponse.model_validate(
            self._get("/token-list", params={"chainId": int(chain_id)})
        )

    def create_order(
        self,
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
    ) -> CreateOrderResponse:
        """``GET /dln/order/create-tx`` — build a cross-chain order + its tx.

        Works for both EVM and Solana source chains; the returned ``tx`` carries
        ``to``/``value`` for EVM sources and only ``data`` for Solana.
        """
        params = build_create_order_params(
            src_chain_id=src_chain_id,
            src_chain_token_in=src_chain_token_in,
            src_chain_token_in_amount=src_chain_token_in_amount,
            dst_chain_id=dst_chain_id,
            dst_chain_token_out=dst_chain_token_out,
            dst_chain_token_out_recipient=dst_chain_token_out_recipient,
            sender_address=sender_address,
            dst_chain_token_out_amount=dst_chain_token_out_amount,
            src_chain_order_authority_address=src_chain_order_authority_address,
            dst_chain_order_authority_address=dst_chain_order_authority_address,
            referral_code=referral_code,
            affiliate_fee_percent=affiliate_fee_percent,
            affiliate_fee_recipient=affiliate_fee_recipient,
            prepend_operating_expenses=prepend_operating_expenses,
            extra=extra,
        )
        return CreateOrderResponse.model_validate(self._get("/dln/order/create-tx", params=params))

    def get_order_status(self, order_id: str) -> OrderStatus:
        """``GET /dln/order/{id}/status`` — lightweight status of an order."""
        return OrderStatus.model_validate(self._get(f"/dln/order/{order_id}/status"))

    def get_order(self, order_id: str) -> OrderDetails:
        """``GET /dln/order/{id}`` — full order struct + status."""
        return OrderDetails.model_validate(self._get(f"/dln/order/{order_id}"))

    def poll_status(
        self,
        order_id: str,
        *,
        interval: float = 5.0,
        timeout: float = 600.0,
    ) -> OrderStatus:
        """Poll an order's status until it reaches a terminal state.

        Returns the terminal :class:`OrderStatus`. Raises :class:`TimeoutError`
        if ``timeout`` seconds elapse first. ``interval=0`` polls without
        sleeping (useful in tests).
        """
        deadline = time.monotonic() + timeout
        while True:
            status = self.get_order_status(order_id)
            if status.status in TERMINAL_STATUSES:
                return status
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Order {order_id} did not reach a terminal status within "
                    f"{timeout}s (last status: {status.status})"
                )
            if interval:
                time.sleep(interval)


class AsyncDebridgeClient(_BaseClient):
    """Asynchronous counterpart of :class:`DebridgeClient`."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(base_url)
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    # -- lifecycle --

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncDebridgeClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    # -- internal --

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = await self._client.get(f"{self.base_url}{path}", params=params)
        return parse_response(response)

    # -- endpoints --

    async def get_supported_chains(self) -> SupportedChainsResponse:
        return SupportedChainsResponse.model_validate(await self._get("/supported-chains-info"))

    async def get_token_list(self, chain_id: int) -> TokenListResponse:
        return TokenListResponse.model_validate(
            await self._get("/token-list", params={"chainId": int(chain_id)})
        )

    async def create_order(
        self,
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
    ) -> CreateOrderResponse:
        params = build_create_order_params(
            src_chain_id=src_chain_id,
            src_chain_token_in=src_chain_token_in,
            src_chain_token_in_amount=src_chain_token_in_amount,
            dst_chain_id=dst_chain_id,
            dst_chain_token_out=dst_chain_token_out,
            dst_chain_token_out_recipient=dst_chain_token_out_recipient,
            sender_address=sender_address,
            dst_chain_token_out_amount=dst_chain_token_out_amount,
            src_chain_order_authority_address=src_chain_order_authority_address,
            dst_chain_order_authority_address=dst_chain_order_authority_address,
            referral_code=referral_code,
            affiliate_fee_percent=affiliate_fee_percent,
            affiliate_fee_recipient=affiliate_fee_recipient,
            prepend_operating_expenses=prepend_operating_expenses,
            extra=extra,
        )
        return CreateOrderResponse.model_validate(
            await self._get("/dln/order/create-tx", params=params)
        )

    async def get_order_status(self, order_id: str) -> OrderStatus:
        return OrderStatus.model_validate(await self._get(f"/dln/order/{order_id}/status"))

    async def get_order(self, order_id: str) -> OrderDetails:
        return OrderDetails.model_validate(await self._get(f"/dln/order/{order_id}"))

    async def poll_status(
        self,
        order_id: str,
        *,
        interval: float = 5.0,
        timeout: float = 600.0,
    ) -> OrderStatus:
        import asyncio

        deadline = time.monotonic() + timeout
        while True:
            status = await self.get_order_status(order_id)
            if status.status in TERMINAL_STATUSES:
                return status
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Order {order_id} did not reach a terminal status within "
                    f"{timeout}s (last status: {status.status})"
                )
            if interval:
                await asyncio.sleep(interval)
