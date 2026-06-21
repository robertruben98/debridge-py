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

    Wraps the public DLN endpoints (quotes, order creation, status) with typed
    requests and responses. Every method raises :class:`DebridgeAPIError` on an
    API error (including HTTP-200 error bodies such as compliance blocks).

    Use it as a context manager so the underlying ``httpx`` connection pool is
    closed for you; otherwise call :meth:`close` when done.

    Example::

        from debridge import DebridgeClient
        from debridge.constants import ChainId

        with DebridgeClient() as client:
            chains = client.get_supported_chains()
            order = client.create_order(
                src_chain_id=ChainId.BASE,
                src_chain_token_in="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                src_chain_token_in_amount="10000000",
                dst_chain_id=ChainId.ARBITRUM,
                dst_chain_token_out="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                dst_chain_token_out_recipient="0xYourRecipient",
                sender_address="0xYourSender",
            )
            final = client.poll_status(order.order_id)
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        """Create a synchronous client.

        Args:
            base_url: DLN API base URL. Defaults to the public endpoint
                (:data:`debridge.constants.DEFAULT_BASE_URL`); a trailing slash
                is tolerated. Point this at a compatible proxy if needed.
            timeout: Per-request timeout in seconds, applied when this client
                creates its own ``httpx.Client``. Ignored if ``client`` is given.
            client: An existing ``httpx.Client`` to reuse. When supplied, the
                caller owns its lifecycle and :meth:`close` will not close it.
        """
        super().__init__(base_url)
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    # -- lifecycle --

    def close(self) -> None:
        """Close the underlying HTTP client.

        No-op when an external ``httpx.Client`` was injected via the
        constructor (the caller owns that client's lifecycle).
        """
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> DebridgeClient:
        """Enter the runtime context and return this client."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        """Exit the runtime context, closing the client via :meth:`close`."""
        self.close()

    # -- internal --

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self._client.get(f"{self.base_url}{path}", params=params)
        return parse_response(response)

    # -- endpoints --

    def get_supported_chains(self) -> SupportedChainsResponse:
        """Fetch the chains the DLN currently supports.

        Calls ``GET /supported-chains-info``.

        Returns:
            A :class:`SupportedChainsResponse` listing every supported chain.

        Raises:
            DebridgeAPIError: If the API returns an error.
        """
        return SupportedChainsResponse.model_validate(self._get("/supported-chains-info"))

    def get_token_list(self, chain_id: int) -> TokenListResponse:
        """Fetch the tradable token list for a chain.

        Calls ``GET /token-list``.

        Args:
            chain_id: deBridge chain id (an ``int`` or a
                :class:`debridge.constants.ChainId` member).

        Returns:
            A :class:`TokenListResponse` mapping token address to metadata.

        Raises:
            DebridgeAPIError: If the API returns an error.
        """
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
        """Quote and build a cross-chain order plus its source-chain transaction.

        Calls ``GET /dln/order/create-tx``. Works for both EVM and Solana source
        chains; the returned ``tx`` carries ``to``/``value`` for EVM sources and
        only ``data`` for Solana (see :class:`debridge.models.Transaction`).

        Args:
            src_chain_id: Source chain id (int or ``ChainId``).
            src_chain_token_in: Input token address on the source chain
                (0x-hex for EVM, base58 mint for Solana; native sentinels in
                :mod:`debridge.constants`).
            src_chain_token_in_amount: Input amount in the token's smallest unit.
            dst_chain_id: Destination chain id (int or ``ChainId``).
            dst_chain_token_out: Output token address on the destination chain.
            dst_chain_token_out_recipient: Address that receives the output.
            sender_address: Address sending the source transaction.
            dst_chain_token_out_amount: Desired output amount, or ``"auto"``
                (default) to let the API quote the best available output.
            src_chain_order_authority_address: Authority that can patch/cancel on
                the source chain. Defaults to ``sender_address``.
            dst_chain_order_authority_address: Authority on the destination
                chain. Defaults to ``dst_chain_token_out_recipient``.
            referral_code: Optional integer referral code.
            affiliate_fee_percent: Optional affiliate fee percentage to charge.
            affiliate_fee_recipient: Address that receives the affiliate fee.
            prepend_operating_expenses: Whether to add operating expenses on top
                of the input amount instead of deducting them from the output.
            extra: Additional raw query params, merged last (escape hatch for
                params not yet modelled here).

        Returns:
            A :class:`CreateOrderResponse` with the quote, the unsigned ``tx``,
            and the resulting ``order_id``.

        Raises:
            DebridgeAPIError: If the API rejects the request (e.g. unsupported
                chain, blocked address) — including HTTP-200 compliance blocks.

        Example:
            EVM -> EVM (10 USDC on Base to USDC on Arbitrum)::

                order = client.create_order(
                    src_chain_id=ChainId.BASE,
                    src_chain_token_in="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    src_chain_token_in_amount="10000000",
                    dst_chain_id=ChainId.ARBITRUM,
                    dst_chain_token_out="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                    dst_chain_token_out_recipient="0xRecipient",
                    sender_address="0xSender",
                )
                print(order.tx.to, order.tx.value)  # EVM call to sign & send

            EVM -> Solana (Base USDC to USDC on Solana)::

                order = client.create_order(
                    src_chain_id=ChainId.BASE,
                    src_chain_token_in="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    src_chain_token_in_amount="10000000",
                    dst_chain_id=ChainId.SOLANA,
                    dst_chain_token_out="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    dst_chain_token_out_recipient="GZ1WYUw1...",  # base58 address
                    sender_address="0xSender",
                )
                # Output recipient is on Solana; tx is still an EVM call (source
                # is Base). For a Solana *source*, order.tx.to/value are None and
                # order.tx.data is the serialized versioned tx as hex.
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
        """Fetch the lightweight status of an order.

        Calls ``GET /dln/order/{id}/status``.

        Args:
            order_id: The order id (0x-hex), e.g. from
                :attr:`CreateOrderResponse.order_id`.

        Returns:
            An :class:`OrderStatus` with the current ``status`` string.

        Raises:
            DebridgeAPIError: If the order is unknown or the id is malformed.
        """
        return OrderStatus.model_validate(self._get(f"/dln/order/{order_id}/status"))

    def get_order(self, order_id: str) -> OrderDetails:
        """Fetch full order details, including the decoded order struct.

        Calls ``GET /dln/order/{id}``.

        Args:
            order_id: The order id (0x-hex).

        Returns:
            An :class:`OrderDetails` with status, external-call state, and the
            on-chain :class:`debridge.models.OrderStruct`.

        Raises:
            DebridgeAPIError: If the order is unknown or the id is malformed.
        """
        return OrderDetails.model_validate(self._get(f"/dln/order/{order_id}"))

    def poll_status(
        self,
        order_id: str,
        *,
        interval: float = 5.0,
        timeout: float = 600.0,
    ) -> OrderStatus:
        """Poll an order's status until it reaches a terminal state.

        Repeatedly calls :meth:`get_order_status`, sleeping ``interval`` seconds
        between checks, until the status is in
        :data:`debridge.constants.TERMINAL_STATUSES` (e.g. ``"Fulfilled"``).

        Args:
            order_id: The order id to poll.
            interval: Seconds to wait between polls. ``0`` polls without
                sleeping (useful in tests).
            timeout: Maximum total seconds to wait before giving up.

        Returns:
            The terminal :class:`OrderStatus`.

        Raises:
            TimeoutError: If no terminal state is reached within ``timeout``.
            DebridgeAPIError: If a status request fails.

        Example::

            # After broadcasting order.tx on the source chain:
            final = client.poll_status(order.order_id, interval=5, timeout=600)
            print(final.status)  # e.g. "Fulfilled"
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
    """Asynchronous counterpart of :class:`DebridgeClient`.

    Exposes the same endpoints as coroutines, backed by ``httpx.AsyncClient``.
    Use it as an async context manager so the connection pool is closed for you;
    otherwise call :meth:`aclose`.

    Example::

        import asyncio
        from debridge import AsyncDebridgeClient

        async def main():
            async with AsyncDebridgeClient() as client:
                chains = await client.get_supported_chains()
                print(len(chains.chains))

        asyncio.run(main())
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Create an asynchronous client.

        Args:
            base_url: DLN API base URL. Defaults to the public endpoint
                (:data:`debridge.constants.DEFAULT_BASE_URL`); a trailing slash
                is tolerated.
            timeout: Per-request timeout in seconds, applied when this client
                creates its own ``httpx.AsyncClient``. Ignored if ``client`` is
                given.
            client: An existing ``httpx.AsyncClient`` to reuse. When supplied,
                the caller owns its lifecycle and :meth:`aclose` will not close
                it.
        """
        super().__init__(base_url)
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None

    # -- lifecycle --

    async def aclose(self) -> None:
        """Close the underlying async HTTP client.

        No-op when an external ``httpx.AsyncClient`` was injected via the
        constructor (the caller owns that client's lifecycle).
        """
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncDebridgeClient:
        """Enter the async runtime context and return this client."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        """Exit the async runtime context, closing the client via :meth:`aclose`."""
        await self.aclose()

    # -- internal --

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = await self._client.get(f"{self.base_url}{path}", params=params)
        return parse_response(response)

    # -- endpoints --

    async def get_supported_chains(self) -> SupportedChainsResponse:
        """Fetch the chains the DLN currently supports.

        Calls ``GET /supported-chains-info``.

        Returns:
            A :class:`SupportedChainsResponse` listing every supported chain.

        Raises:
            DebridgeAPIError: If the API returns an error.
        """
        return SupportedChainsResponse.model_validate(await self._get("/supported-chains-info"))

    async def get_token_list(self, chain_id: int) -> TokenListResponse:
        """Fetch the tradable token list for a chain.

        Calls ``GET /token-list``.

        Args:
            chain_id: deBridge chain id (an ``int`` or a
                :class:`debridge.constants.ChainId` member).

        Returns:
            A :class:`TokenListResponse` mapping token address to metadata.

        Raises:
            DebridgeAPIError: If the API returns an error.
        """
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
        """Quote and build a cross-chain order plus its source-chain transaction.

        Async equivalent of :meth:`DebridgeClient.create_order`; see that method
        for full argument and return documentation and EVM/Solana examples.

        Args:
            src_chain_id: Source chain id (int or ``ChainId``).
            src_chain_token_in: Input token address on the source chain.
            src_chain_token_in_amount: Input amount in the token's smallest unit.
            dst_chain_id: Destination chain id (int or ``ChainId``).
            dst_chain_token_out: Output token address on the destination chain.
            dst_chain_token_out_recipient: Address that receives the output.
            sender_address: Address sending the source transaction.
            dst_chain_token_out_amount: Desired output amount, or ``"auto"``.
            src_chain_order_authority_address: Source-chain order authority;
                defaults to ``sender_address``.
            dst_chain_order_authority_address: Destination-chain order authority;
                defaults to ``dst_chain_token_out_recipient``.
            referral_code: Optional integer referral code.
            affiliate_fee_percent: Optional affiliate fee percentage.
            affiliate_fee_recipient: Address that receives the affiliate fee.
            prepend_operating_expenses: Add operating expenses on top of the
                input instead of deducting from the output.
            extra: Additional raw query params, merged last.

        Returns:
            A :class:`CreateOrderResponse` with the quote, unsigned ``tx``, and
            the resulting ``order_id``.

        Raises:
            DebridgeAPIError: If the API rejects the request (including HTTP-200
                compliance blocks).
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
        return CreateOrderResponse.model_validate(
            await self._get("/dln/order/create-tx", params=params)
        )

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Fetch the lightweight status of an order.

        Calls ``GET /dln/order/{id}/status``.

        Args:
            order_id: The order id (0x-hex).

        Returns:
            An :class:`OrderStatus` with the current ``status`` string.

        Raises:
            DebridgeAPIError: If the order is unknown or the id is malformed.
        """
        return OrderStatus.model_validate(await self._get(f"/dln/order/{order_id}/status"))

    async def get_order(self, order_id: str) -> OrderDetails:
        """Fetch full order details, including the decoded order struct.

        Calls ``GET /dln/order/{id}``.

        Args:
            order_id: The order id (0x-hex).

        Returns:
            An :class:`OrderDetails` with status, external-call state, and the
            on-chain :class:`debridge.models.OrderStruct`.

        Raises:
            DebridgeAPIError: If the order is unknown or the id is malformed.
        """
        return OrderDetails.model_validate(await self._get(f"/dln/order/{order_id}"))

    async def poll_status(
        self,
        order_id: str,
        *,
        interval: float = 5.0,
        timeout: float = 600.0,
    ) -> OrderStatus:
        """Poll an order's status until it reaches a terminal state.

        Async equivalent of :meth:`DebridgeClient.poll_status`; awaits
        :meth:`get_order_status` and sleeps via ``asyncio.sleep`` between checks.

        Args:
            order_id: The order id to poll.
            interval: Seconds to wait between polls. ``0`` polls without
                sleeping (useful in tests).
            timeout: Maximum total seconds to wait before giving up.

        Returns:
            The terminal :class:`OrderStatus`.

        Raises:
            TimeoutError: If no terminal state is reached within ``timeout``.
            DebridgeAPIError: If a status request fails.

        Example::

            final = await client.poll_status(order.order_id, interval=5, timeout=600)
            print(final.status)  # e.g. "Fulfilled"
        """
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
