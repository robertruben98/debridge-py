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
    """Base config shared by every model: alias support + forward-compat."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# --- supported-chains-info ---


class SupportedChain(_Model):
    chain_id: int = Field(alias="chainId")
    original_chain_id: int = Field(alias="originalChainId")
    chain_name: str = Field(alias="chainName")


class SupportedChainsResponse(_Model):
    chains: List[SupportedChain]


# --- token-list ---


class TokenInfo(_Model):
    symbol: str
    name: str
    decimals: int
    address: str
    logo_uri: Optional[str] = Field(default=None, alias="logoURI")
    tags: List[str] = Field(default_factory=list)
    eip2612: Optional[bool] = None
    is_native: Optional[bool] = Field(default=None, alias="isNative")


class TokenListResponse(_Model):
    tokens: Dict[str, TokenInfo]


# --- dln/order/create-tx ---


class TokenAmount(_Model):
    """A token leg in an order estimation (src in / dst out)."""

    chain_id: int = Field(alias="chainId")
    address: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimals: Optional[int] = None
    amount: str
    recommended_amount: Optional[str] = Field(default=None, alias="recommendedAmount")
    max_theoretical_amount: Optional[str] = Field(default=None, alias="maxTheoreticalAmount")
    approximate_usd_value: Optional[float] = Field(default=None, alias="approximateUsdValue")


class CostDetail(_Model):
    chain: Optional[str] = None
    token_in: Optional[str] = Field(default=None, alias="tokenIn")
    token_out: Optional[str] = Field(default=None, alias="tokenOut")
    amount_in: Optional[str] = Field(default=None, alias="amountIn")
    amount_out: Optional[str] = Field(default=None, alias="amountOut")
    type: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class Estimation(_Model):
    src_chain_token_in: TokenAmount = Field(alias="srcChainTokenIn")
    dst_chain_token_out: TokenAmount = Field(alias="dstChainTokenOut")
    costs_details: List[CostDetail] = Field(default_factory=list, alias="costsDetails")
    recommended_slippage: Optional[float] = Field(default=None, alias="recommendedSlippage")


class Transaction(_Model):
    """The transaction to broadcast on the source chain.

    For EVM sources, ``to`` and ``value`` are present (an EVM call). For Solana
    sources the API returns only ``data`` (the serialized versioned transaction
    encoded as a hex string).
    """

    data: str
    to: Optional[str] = None
    value: Optional[str] = None


class OrderMetadata(_Model):
    approximate_fulfillment_delay: Optional[int] = Field(
        default=None, alias="approximateFulfillmentDelay"
    )
    salt: Optional[int] = None
    metadata: Optional[str] = None


class EstimatedTransactionFee(_Model):
    total: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class CreateOrderResponse(_Model):
    order_id: str = Field(alias="orderId")
    estimation: Estimation
    tx: Transaction
    order: Optional[OrderMetadata] = None
    fix_fee: Optional[str] = Field(default=None, alias="fixFee")
    protocol_fee: Optional[str] = Field(default=None, alias="protocolFee")
    estimated_transaction_fee: Optional[EstimatedTransactionFee] = Field(
        default=None, alias="estimatedTransactionFee"
    )
    user_points: Optional[float] = Field(default=None, alias="userPoints")
    integrator_points: Optional[float] = Field(default=None, alias="integratorPoints")
    protocol_fee_approximate_usd_value: Optional[float] = Field(
        default=None, alias="protocolFeeApproximateUsdValue"
    )
    usd_price_impact: Optional[float] = Field(default=None, alias="usdPriceImpact")


# --- dln/order/{id}/status and /dln/order/{id} ---


class OrderStatus(_Model):
    order_id: str = Field(alias="orderId")
    status: str


class Offer(_Model):
    chain_id: int = Field(alias="chainId")
    token_address: str = Field(alias="tokenAddress")
    amount: str


class OrderStruct(_Model):
    maker_order_nonce: Optional[int] = Field(default=None, alias="makerOrderNonce")
    maker_src: Optional[str] = Field(default=None, alias="makerSrc")
    give_offer: Offer = Field(alias="giveOffer")
    take_offer: Offer = Field(alias="takeOffer")
    receiver_dst: Optional[str] = Field(default=None, alias="receiverDst")


class OrderDetails(_Model):
    order_id: str = Field(alias="orderId")
    status: str
    external_call_state: Optional[str] = Field(default=None, alias="externalCallState")
    order_struct: OrderStruct = Field(alias="orderStruct")
