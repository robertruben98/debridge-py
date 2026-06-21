"""Pydantic models for deBridge DLN API payloads.

These models intentionally use ``extra="allow"`` so that fields the API adds
over time (points, new fee breakdowns, etc.) do not break parsing. Field names
are snake_case in Python and aliased to the API's camelCase via
``populate_by_name`` + ``alias``.

Addresses and amounts are kept as strings because they must represent both EVM
(0x-hex) and Solana (base58) values, and on-chain amounts routinely exceed the
safe integer range. Callers convert as needed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    """Base config shared by every model: alias support + forward-compat.

    ``populate_by_name=True`` lets models be built from either the API's
    camelCase aliases or the snake_case field names, and ``extra="allow"``
    preserves any fields deBridge adds in the future instead of rejecting them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# --- supported-chains-info ---


class SupportedChain(_Model):
    """A single chain entry from ``GET /supported-chains-info``.

    Note that deBridge's internal ``chain_id`` differs from the chain's native
    id for non-EVM/L2 chains (e.g. Solana is ``7565164``). Use ``chain_id`` when
    talking to this API and ``original_chain_id`` to map back to the chain's
    canonical id.
    """

    chain_id: int = Field(
        alias="chainId",
        description="deBridge internal chain id; use this in API calls.",
    )
    original_chain_id: int = Field(
        alias="originalChainId",
        description="The chain's native/canonical id (e.g. EVM chain id).",
    )
    chain_name: str = Field(alias="chainName", description="Human-readable chain name.")


class SupportedChainsResponse(_Model):
    """Response of ``GET /supported-chains-info`` — the list of supported chains."""

    chains: List[SupportedChain] = Field(description="All chains the DLN currently supports.")


# --- token-list ---


class TokenInfo(_Model):
    """Metadata for one token, as returned by ``GET /token-list``."""

    symbol: str = Field(description="Ticker symbol, e.g. 'USDC'.")
    name: str = Field(description="Full token name, e.g. 'USD Coin'.")
    decimals: int = Field(description="Number of decimal places the token uses.")
    address: str = Field(
        description="Token contract address (0x-hex for EVM, base58 mint for Solana)."
    )
    logo_uri: Optional[str] = Field(
        default=None, alias="logoURI", description="URL of the token logo, if known."
    )
    tags: List[str] = Field(
        default_factory=list, description="Free-form classification tags from deBridge."
    )
    eip2612: Optional[bool] = Field(
        default=None, description="Whether the token supports EIP-2612 permit (EVM only)."
    )
    is_native: Optional[bool] = Field(
        default=None,
        alias="isNative",
        description="True if this is the chain's native gas token.",
    )


class TokenListResponse(_Model):
    """Response of ``GET /token-list`` — tokens keyed by their address."""

    tokens: Dict[str, TokenInfo] = Field(description="Mapping of token address -> token metadata.")


# --- dln/order/create-tx ---


class TokenAmount(_Model):
    """A token leg in an order estimation (the input on src, the output on dst).

    The ``recommended_*`` / ``max_theoretical_*`` fields are populated for the
    destination leg, describing how much the recipient is expected to receive.
    """

    chain_id: int = Field(alias="chainId", description="deBridge chain id of this leg.")
    address: str = Field(description="Token address on that chain.")
    name: Optional[str] = Field(default=None, description="Full token name, if known.")
    symbol: Optional[str] = Field(default=None, description="Ticker symbol, if known.")
    decimals: Optional[int] = Field(default=None, description="Token decimals, if known.")
    amount: str = Field(description="Amount in the token's smallest unit (as a string).")
    recommended_amount: Optional[str] = Field(
        default=None,
        alias="recommendedAmount",
        description="Recommended output amount for the destination leg.",
    )
    max_theoretical_amount: Optional[str] = Field(
        default=None,
        alias="maxTheoreticalAmount",
        description="Best-case output amount ignoring market/taker margin.",
    )
    approximate_usd_value: Optional[float] = Field(
        default=None,
        alias="approximateUsdValue",
        description="Approximate USD value of this leg.",
    )


class CostDetail(_Model):
    """A single line item in the order's cost breakdown (one fee or conversion step)."""

    chain: Optional[str] = Field(default=None, description="Chain id this cost applies to.")
    token_in: Optional[str] = Field(
        default=None, alias="tokenIn", description="Input token address for this step."
    )
    token_out: Optional[str] = Field(
        default=None, alias="tokenOut", description="Output token address for this step."
    )
    amount_in: Optional[str] = Field(
        default=None, alias="amountIn", description="Amount entering this step."
    )
    amount_out: Optional[str] = Field(
        default=None, alias="amountOut", description="Amount leaving this step."
    )
    type: Optional[str] = Field(
        default=None,
        description="Cost type, e.g. 'DlnProtocolFee', 'TakerMargin', "
        "'EstimatedOperatingExpenses'.",
    )
    payload: Optional[Dict[str, Any]] = Field(
        default=None, description="Type-specific extra fields (fee amount, bps, etc.)."
    )


class Estimation(_Model):
    """The quote portion of a create-order response: legs, costs, and slippage."""

    src_chain_token_in: TokenAmount = Field(
        alias="srcChainTokenIn", description="The input token/amount on the source chain."
    )
    dst_chain_token_out: TokenAmount = Field(
        alias="dstChainTokenOut",
        description="The estimated output token/amount on the destination chain.",
    )
    costs_details: List[CostDetail] = Field(
        default_factory=list,
        alias="costsDetails",
        description="Ordered breakdown of every fee and conversion step.",
    )
    recommended_slippage: Optional[float] = Field(
        default=None,
        alias="recommendedSlippage",
        description="Slippage (percent) deBridge recommends for this order.",
    )


class Transaction(_Model):
    """The transaction to broadcast on the source chain.

    For EVM sources, ``to`` and ``value`` are present (an EVM call). For Solana
    sources the API returns only ``data`` (the serialized versioned transaction
    encoded as a hex string), and ``to``/``value`` are ``None``. Inspect which
    fields are set to decide how to sign and broadcast.
    """

    data: str = Field(description="Calldata (EVM) or the serialized versioned tx as hex (Solana).")
    to: Optional[str] = Field(
        default=None, description="Target contract address (EVM only; None for Solana)."
    )
    value: Optional[str] = Field(
        default=None, description="Native value to send in wei (EVM only; None for Solana)."
    )


class OrderMetadata(_Model):
    """Auxiliary order data returned alongside the transaction."""

    approximate_fulfillment_delay: Optional[int] = Field(
        default=None,
        alias="approximateFulfillmentDelay",
        description="Estimated seconds until the order is fulfilled on the destination.",
    )
    salt: Optional[int] = Field(
        default=None, description="Unique salt that identifies this order build."
    )
    metadata: Optional[str] = Field(default=None, description="Opaque hex-encoded order metadata.")


class EstimatedTransactionFee(_Model):
    """Estimated cost of broadcasting the source-chain transaction itself."""

    total: Optional[str] = Field(
        default=None, description="Total estimated network fee in the chain's smallest unit."
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Chain-specific breakdown (gas limit/base fee for EVM, "
        "rent/priority fee for Solana).",
    )


class CreateOrderResponse(_Model):
    """Full response of ``GET /dln/order/create-tx``.

    Bundles the quote (:attr:`estimation`), the unsigned source-chain
    :attr:`tx` to broadcast, the resulting :attr:`order_id`, and fee details.
    The same shape is returned for EVM and Solana sources; only :attr:`tx`
    varies (see :class:`Transaction`).

    Example::

        order = client.create_order(...)
        print(order.order_id)
        print(order.estimation.dst_chain_token_out.amount)  # expected output
        print(order.tx.to, order.tx.value, order.tx.data)   # tx to sign & send
    """

    order_id: str = Field(
        alias="orderId", description="Deterministic id of the order to be created."
    )
    estimation: Estimation = Field(description="Quote: legs, cost breakdown, slippage.")
    tx: Transaction = Field(description="Unsigned transaction to broadcast on the source chain.")
    order: Optional[OrderMetadata] = Field(
        default=None, description="Auxiliary order metadata (salt, delay, etc.)."
    )
    fix_fee: Optional[str] = Field(
        default=None,
        alias="fixFee",
        description="Fixed protocol fee in the source chain's native token.",
    )
    protocol_fee: Optional[str] = Field(
        default=None, alias="protocolFee", description="Variable protocol fee (token units)."
    )
    estimated_transaction_fee: Optional[EstimatedTransactionFee] = Field(
        default=None,
        alias="estimatedTransactionFee",
        description="Estimated network cost of broadcasting the source tx.",
    )
    user_points: Optional[float] = Field(
        default=None, alias="userPoints", description="deBridge loyalty points for the user."
    )
    integrator_points: Optional[float] = Field(
        default=None,
        alias="integratorPoints",
        description="deBridge loyalty points for the integrator.",
    )
    protocol_fee_approximate_usd_value: Optional[float] = Field(
        default=None,
        alias="protocolFeeApproximateUsdValue",
        description="Approximate USD value of the protocol fee.",
    )
    usd_price_impact: Optional[float] = Field(
        default=None,
        alias="usdPriceImpact",
        description="Approximate price impact of the swap, as a percentage.",
    )


# --- dln/order/{id}/status and /dln/order/{id} ---


class OrderStatus(_Model):
    """Lightweight order status from ``GET /dln/order/{id}/status``.

    ``status`` is a string such as ``"Created"``, ``"Fulfilled"``,
    ``"SentUnlock"``, ``"ClaimedUnlock"``, ``"OrderCancelled"`` — see
    :data:`debridge.constants.TERMINAL_STATUSES` for the states treated as final.
    """

    order_id: str = Field(alias="orderId", description="The order's id.")
    status: str = Field(description="Current order status string.")


class Offer(_Model):
    """One side of an order: the token, chain, and amount being given or taken."""

    chain_id: int = Field(alias="chainId", description="deBridge chain id of this side.")
    token_address: str = Field(alias="tokenAddress", description="Token address on that chain.")
    amount: str = Field(description="Amount in the token's smallest unit (as a string).")


class OrderStruct(_Model):
    """The on-chain order structure: who gives what, who receives what, and where."""

    maker_order_nonce: Optional[int] = Field(
        default=None, alias="makerOrderNonce", description="Maker's per-order nonce."
    )
    maker_src: Optional[str] = Field(
        default=None, alias="makerSrc", description="Maker (sender) address on the source chain."
    )
    give_offer: Offer = Field(
        alias="giveOffer", description="What the maker provides on the source chain."
    )
    take_offer: Offer = Field(
        alias="takeOffer", description="What is delivered on the destination chain."
    )
    receiver_dst: Optional[str] = Field(
        default=None,
        alias="receiverDst",
        description="Recipient address on the destination chain.",
    )


class OrderDetails(_Model):
    """Full order detail from ``GET /dln/order/{id}`` — status plus the order struct."""

    order_id: str = Field(alias="orderId", description="The order's id.")
    status: str = Field(description="Current order status string.")
    external_call_state: Optional[str] = Field(
        default=None,
        alias="externalCallState",
        description="State of any attached external call, e.g. 'NoExtCall'.",
    )
    order_struct: OrderStruct = Field(
        alias="orderStruct", description="The decoded on-chain order structure."
    )
