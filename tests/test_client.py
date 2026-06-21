"""Tests for the synchronous DebridgeClient using respx (no real network)."""

from typing import Iterator

import httpx
import pytest
import respx

from debridge import DebridgeAPIError, DebridgeClient
from debridge.constants import ChainId

BASE = "https://dln.debridge.finance/v1.0"

CHAINS = {"chains": [{"chainId": 1, "originalChainId": 1, "chainName": "Ethereum"}]}
TOKENS = {
    "tokens": {
        "0x0000000000000000000000000000000000000000": {
            "symbol": "ETH",
            "name": "Ethereum",
            "decimals": 18,
            "address": "0x0000000000000000000000000000000000000000",
            "isNative": True,
        }
    }
}
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
STATUS = {"status": "Fulfilled", "orderId": "0xabc"}
DETAILS = {
    "orderId": "0xabc",
    "status": "Fulfilled",
    "externalCallState": "NoExtCall",
    "orderStruct": {
        "giveOffer": {"chainId": 8453, "tokenAddress": "0x83", "amount": "10000000"},
        "takeOffer": {"chainId": 42161, "tokenAddress": "0xaf", "amount": "9775827"},
        "receiverDst": "0xd8",
    },
}


@pytest.fixture
def client() -> Iterator[DebridgeClient]:
    c = DebridgeClient()
    yield c
    c.close()


@respx.mock
def test_get_supported_chains(client: DebridgeClient) -> None:
    route = respx.get(f"{BASE}/supported-chains-info").mock(
        return_value=httpx.Response(200, json=CHAINS)
    )
    resp = client.get_supported_chains()
    assert route.called
    assert resp.chains[0].chain_name == "Ethereum"


@respx.mock
def test_get_token_list_passes_chain_id(client: DebridgeClient) -> None:
    route = respx.get(f"{BASE}/token-list").mock(return_value=httpx.Response(200, json=TOKENS))
    resp = client.get_token_list(chain_id=8453)
    assert route.called
    assert route.calls.last.request.url.params["chainId"] == "8453"
    assert resp.tokens["0x0000000000000000000000000000000000000000"].symbol == "ETH"


@respx.mock
def test_get_token_list_accepts_chain_id_enum(client: DebridgeClient) -> None:
    # IntEnum must render as a plain number, not "ChainId.BASE".
    route = respx.get(f"{BASE}/token-list").mock(return_value=httpx.Response(200, json=TOKENS))
    client.get_token_list(chain_id=ChainId.BASE)
    assert route.calls.last.request.url.params["chainId"] == "8453"


@respx.mock
def test_create_order_builds_query_and_parses(client: DebridgeClient) -> None:
    route = respx.get(f"{BASE}/dln/order/create-tx").mock(
        return_value=httpx.Response(200, json=CREATE_TX)
    )
    resp = client.create_order(
        src_chain_id=8453,
        src_chain_token_in="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
        src_chain_token_in_amount="10000000",
        dst_chain_id=42161,
        dst_chain_token_out="0xaf88d065e77c8cc2239327c5edb3a432268e5831",
        dst_chain_token_out_recipient="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        sender_address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    )
    assert route.called
    params = route.calls.last.request.url.params
    assert params["srcChainId"] == "8453"
    assert params["dstChainTokenOutAmount"] == "auto"  # default
    assert params["dstChainTokenOutRecipient"].startswith("0xd8")
    assert resp.order_id == "0xabc"
    assert resp.tx.to == "0xeF"


@respx.mock
def test_create_order_explicit_out_amount_overrides_auto(client: DebridgeClient) -> None:
    respx.get(f"{BASE}/dln/order/create-tx").mock(return_value=httpx.Response(200, json=CREATE_TX))
    client.create_order(
        src_chain_id=8453,
        src_chain_token_in="0x83",
        src_chain_token_in_amount="10000000",
        dst_chain_id=42161,
        dst_chain_token_out="0xaf",
        dst_chain_token_out_recipient="0xd8",
        sender_address="0xd8",
        dst_chain_token_out_amount="9500000",
    )
    params = respx.calls.last.request.url.params
    assert params["dstChainTokenOutAmount"] == "9500000"


@respx.mock
def test_get_order_status(client: DebridgeClient) -> None:
    respx.get(f"{BASE}/dln/order/0xabc/status").mock(return_value=httpx.Response(200, json=STATUS))
    status = client.get_order_status("0xabc")
    assert status.status == "Fulfilled"


@respx.mock
def test_get_order(client: DebridgeClient) -> None:
    respx.get(f"{BASE}/dln/order/0xabc").mock(return_value=httpx.Response(200, json=DETAILS))
    details = client.get_order("0xabc")
    assert details.order_struct.give_offer.chain_id == 8453


@respx.mock
def test_http_4xx_error_raises_api_error(client: DebridgeClient) -> None:
    respx.get(f"{BASE}/dln/order/0xbad/status").mock(
        return_value=httpx.Response(
            400,
            json={
                "errorCode": 15,
                "errorId": "UNKNOWN_ORDER",
                "errorMessage": "Order not found.",
                "reqId": "r-1",
            },
        )
    )
    with pytest.raises(DebridgeAPIError) as exc:
        client.get_order_status("0xbad")
    assert exc.value.error_id == "UNKNOWN_ORDER"
    assert exc.value.status_code == 400


@respx.mock
def test_http_200_with_error_body_raises_api_error(client: DebridgeClient) -> None:
    # COMPLIANCE_ADDRESS_BLOCKED is returned with HTTP 200 + an error body.
    respx.get(f"{BASE}/dln/order/create-tx").mock(
        return_value=httpx.Response(
            200,
            json={
                "errorCode": 123,
                "errorId": "COMPLIANCE_ADDRESS_BLOCKED",
                "errorMessage": "address flagged",
                "reqId": "r-2",
            },
        )
    )
    with pytest.raises(DebridgeAPIError) as exc:
        client.create_order(
            src_chain_id=8453,
            src_chain_token_in="0x83",
            src_chain_token_in_amount="10000000",
            dst_chain_id=42161,
            dst_chain_token_out="0xaf",
            dst_chain_token_out_recipient="0xdead",
            sender_address="0xdead",
        )
    assert exc.value.error_id == "COMPLIANCE_ADDRESS_BLOCKED"
    assert exc.value.status_code == 200


@respx.mock
def test_custom_base_url_is_used() -> None:
    custom = "https://my-proxy.example/v1.0"
    respx.get(f"{custom}/supported-chains-info").mock(return_value=httpx.Response(200, json=CHAINS))
    with DebridgeClient(base_url=custom + "/") as c:  # trailing slash tolerated
        c.get_supported_chains()
    assert respx.calls.last.request.url.host == "my-proxy.example"


@respx.mock
def test_context_manager_closes() -> None:
    respx.get(f"{BASE}/supported-chains-info").mock(return_value=httpx.Response(200, json=CHAINS))
    with DebridgeClient() as c:
        c.get_supported_chains()


@respx.mock
def test_poll_status_returns_on_terminal(client: DebridgeClient) -> None:
    # First call: Created (in-flight). Second: Fulfilled (terminal).
    respx.get(f"{BASE}/dln/order/0xabc/status").mock(
        side_effect=[
            httpx.Response(200, json={"status": "Created", "orderId": "0xabc"}),
            httpx.Response(200, json={"status": "Fulfilled", "orderId": "0xabc"}),
        ]
    )
    final = client.poll_status("0xabc", interval=0, timeout=5)
    assert final.status == "Fulfilled"


@respx.mock
def test_poll_status_times_out(client: DebridgeClient) -> None:
    respx.get(f"{BASE}/dln/order/0xabc/status").mock(
        return_value=httpx.Response(200, json={"status": "Created", "orderId": "0xabc"})
    )
    with pytest.raises(TimeoutError):
        client.poll_status("0xabc", interval=0, timeout=0)
