"""Tests for the asynchronous AsyncDebridgeClient using respx."""

import httpx
import pytest
import respx

from debridge import AsyncDebridgeClient, DebridgeAPIError

BASE = "https://dln.debridge.finance/v1.0"

CHAINS = {"chains": [{"chainId": 1, "originalChainId": 1, "chainName": "Ethereum"}]}
CREATE_TX = {
    "orderId": "0xabc",
    "estimation": {
        "srcChainTokenIn": {"chainId": 8453, "address": "0x83", "amount": "10000000"},
        "dstChainTokenOut": {"chainId": 42161, "address": "0xaf", "amount": "9775827"},
        "costsDetails": [],
        "recommendedSlippage": 0,
    },
    "tx": {"data": "0xb930", "to": "0xeF", "value": "1000"},
}


@respx.mock
async def test_async_get_supported_chains() -> None:
    respx.get(f"{BASE}/supported-chains-info").mock(return_value=httpx.Response(200, json=CHAINS))
    async with AsyncDebridgeClient() as client:
        resp = await client.get_supported_chains()
    assert resp.chains[0].chain_name == "Ethereum"


@respx.mock
async def test_async_create_order() -> None:
    respx.get(f"{BASE}/dln/order/create-tx").mock(return_value=httpx.Response(200, json=CREATE_TX))
    async with AsyncDebridgeClient() as client:
        resp = await client.create_order(
            src_chain_id=8453,
            src_chain_token_in="0x83",
            src_chain_token_in_amount="10000000",
            dst_chain_id=42161,
            dst_chain_token_out="0xaf",
            dst_chain_token_out_recipient="0xd8",
            sender_address="0xd8",
        )
    assert resp.order_id == "0xabc"
    assert resp.tx.to == "0xeF"


@respx.mock
async def test_async_error_body_raises() -> None:
    respx.get(f"{BASE}/dln/order/0xbad/status").mock(
        return_value=httpx.Response(
            400,
            json={"errorCode": 15, "errorId": "UNKNOWN_ORDER", "errorMessage": "no"},
        )
    )
    async with AsyncDebridgeClient() as client:
        with pytest.raises(DebridgeAPIError) as exc:
            await client.get_order_status("0xbad")
    assert exc.value.error_id == "UNKNOWN_ORDER"


@respx.mock
async def test_async_poll_status_reaches_terminal() -> None:
    respx.get(f"{BASE}/dln/order/0xabc/status").mock(
        side_effect=[
            httpx.Response(200, json={"status": "Created", "orderId": "0xabc"}),
            httpx.Response(200, json={"status": "Fulfilled", "orderId": "0xabc"}),
        ]
    )
    async with AsyncDebridgeClient() as client:
        final = await client.poll_status("0xabc", interval=0, timeout=5)
    assert final.status == "Fulfilled"
