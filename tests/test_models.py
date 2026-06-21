"""Tests for pydantic models, validated against real deBridge API payloads."""

from debridge.models import (
    CreateOrderResponse,
    OrderDetails,
    OrderStatus,
    SupportedChainsResponse,
    TokenListResponse,
)

# --- captured live payloads (trimmed) ---

CHAINS_PAYLOAD = {
    "chains": [
        {"chainId": 1, "originalChainId": 1, "chainName": "Ethereum"},
        {"chainId": 7565164, "originalChainId": 7565164, "chainName": "Solana"},
        {"chainId": 100000022, "originalChainId": 999, "chainName": "HyperEVM"},
    ]
}

TOKEN_LIST_PAYLOAD = {
    "tokens": {
        "0x0000000000000000000000000000000000000000": {
            "symbol": "ETH",
            "name": "Ethereum",
            "decimals": 18,
            "address": "0x0000000000000000000000000000000000000000",
            "logoURI": "https://example/logo.svg",
            "tags": [],
            "eip2612": False,
            "isNative": True,
        }
    }
}

EVM_CREATE_TX_PAYLOAD = {
    "estimation": {
        "srcChainTokenIn": {
            "chainId": 8453,
            "address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "amount": "10000000",
            "approximateUsdValue": 10,
        },
        "dstChainTokenOut": {
            "chainId": 42161,
            "address": "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "amount": "9775827",
            "recommendedAmount": "9775827",
            "maxTheoreticalAmount": "9775827",
        },
        "costsDetails": [
            {
                "chain": "8453",
                "tokenIn": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "tokenOut": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                "amountIn": "10000000",
                "amountOut": "9996000",
                "type": "DlnProtocolFee",
                "payload": {"feeAmount": "4000", "feeBps": "4"},
            }
        ],
        "recommendedSlippage": 0,
    },
    "tx": {
        "data": "0xb9303701",
        "to": "0xeF4fB24aD0916217251F553c0596F8Edc630EB66",
        "value": "1000000000000000",
    },
    "order": {"approximateFulfillmentDelay": 1, "salt": 1782070864186, "metadata": "0x0101"},
    "orderId": "0x268798c90c925354e603c26e202df577b499f9347253c2c413d151c0581449a0",
    "fixFee": "1000000000000000",
    "protocolFee": "4000",
    "estimatedTransactionFee": {"total": "4160006400000", "details": {"gasLimit": "640000"}},
    "usdPriceImpact": -2.24,
}

SOLANA_CREATE_TX_PAYLOAD = {
    "estimation": {
        "srcChainTokenIn": {
            "chainId": 7565164,
            "address": "11111111111111111111111111111111",
            "name": "Solana",
            "symbol": "SOL",
            "decimals": 9,
            "amount": "1000000000",
        },
        "dstChainTokenOut": {
            "chainId": 8453,
            "address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            "name": "USD Coin",
            "symbol": "USDC",
            "decimals": 6,
            "amount": "9284302",
        },
        "costsDetails": [],
        "recommendedSlippage": 0,
    },
    # Solana source: tx carries only `data`, no `to`/`value`.
    "tx": {"data": "0x0100000000"},
    "order": {"approximateFulfillmentDelay": 1, "salt": 1, "metadata": "0x"},
    "orderId": "0xcbb54ec979f2ad01770dd2f6bc81aa9e52797f37d9da6c5a01ff713a09e67856",
    "fixFee": "0",
    "protocolFee": "4000",
}


def test_supported_chains_parses() -> None:
    resp = SupportedChainsResponse.model_validate(CHAINS_PAYLOAD)
    assert len(resp.chains) == 3
    solana = next(c for c in resp.chains if c.chain_name == "Solana")
    assert solana.chain_id == 7565164
    hyper = next(c for c in resp.chains if c.chain_name == "HyperEVM")
    assert hyper.chain_id == 100000022
    assert hyper.original_chain_id == 999


def test_token_list_parses() -> None:
    resp = TokenListResponse.model_validate(TOKEN_LIST_PAYLOAD)
    eth = resp.tokens["0x0000000000000000000000000000000000000000"]
    assert eth.symbol == "ETH"
    assert eth.decimals == 18
    assert eth.is_native is True


def test_evm_create_order_parses_with_tx_to_and_value() -> None:
    resp = CreateOrderResponse.model_validate(EVM_CREATE_TX_PAYLOAD)
    assert resp.order_id.startswith("0x")
    assert resp.tx.to == "0xeF4fB24aD0916217251F553c0596F8Edc630EB66"
    assert resp.tx.value == "1000000000000000"
    assert resp.tx.data == "0xb9303701"
    assert resp.estimation.dst_chain_token_out.recommended_amount == "9775827"
    assert resp.estimation.recommended_slippage == 0
    assert resp.fix_fee == "1000000000000000"


def test_solana_create_order_parses_without_tx_to_and_value() -> None:
    resp = CreateOrderResponse.model_validate(SOLANA_CREATE_TX_PAYLOAD)
    assert resp.tx.data == "0x0100000000"
    assert resp.tx.to is None
    assert resp.tx.value is None
    assert resp.estimation.src_chain_token_in.symbol == "SOL"


def test_create_order_preserves_unknown_fields_for_forward_compat() -> None:
    # The API adds fields over time (userPoints etc.); we must not choke on them.
    payload = dict(EVM_CREATE_TX_PAYLOAD)
    payload["someBrandNewField"] = {"nested": True}
    resp = CreateOrderResponse.model_validate(payload)
    assert resp.order_id


def test_order_status_parses() -> None:
    status = OrderStatus.model_validate({"status": "Fulfilled", "orderId": "0x5a93"})
    assert status.status == "Fulfilled"
    assert status.order_id == "0x5a93"


def test_order_details_parses() -> None:
    details = OrderDetails.model_validate(
        {
            "orderId": "0x5a93",
            "status": "Fulfilled",
            "externalCallState": "NoExtCall",
            "orderStruct": {
                "makerOrderNonce": 1782070867651,
                "giveOffer": {
                    "chainId": 100000022,
                    "tokenAddress": "0xb88339",
                    "amount": "1000307595",
                },
                "takeOffer": {
                    "chainId": 7565164,
                    "tokenAddress": "METvsvVRapdj9cFLzq4Tr43xK4tAjQfwX76z3n6mWQL",
                    "amount": "5786315492",
                },
                "receiverDst": "5NBgatnfozAUUULsdqNKhTHbqVRmhKR1T6Xz9dL7sM72",
            },
        }
    )
    assert details.status == "Fulfilled"
    assert details.order_struct.give_offer.chain_id == 100000022
    assert details.order_struct.take_offer.token_address.startswith("MET")
