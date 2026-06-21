"""Tests for query-param building and order-authority defaults."""

from debridge._transport import build_create_order_params, normalize_base_url
from debridge.constants import ChainId


def test_normalize_base_url_strips_trailing_slash() -> None:
    assert normalize_base_url("https://x/v1.0/") == "https://x/v1.0"
    assert normalize_base_url("https://x/v1.0") == "https://x/v1.0"


def test_chain_id_intenum_serializes_to_plain_number() -> None:
    # Regression: IntEnum members must render as "8453", not "ChainId.BASE",
    # otherwise the API rejects srcChainId/dstChainId.
    params = build_create_order_params(
        src_chain_id=ChainId.BASE,
        src_chain_token_in="0x83",
        src_chain_token_in_amount="10000000",
        dst_chain_id=ChainId.ARBITRUM,
        dst_chain_token_out="0xaf",
        dst_chain_token_out_recipient="0xd8",
        sender_address="0xd8",
    )
    assert params["srcChainId"] == "8453"
    assert params["dstChainId"] == "42161"


def test_order_authority_defaults_to_sender_and_recipient() -> None:
    params = build_create_order_params(
        src_chain_id=8453,
        src_chain_token_in="0x83",
        src_chain_token_in_amount="10000000",
        dst_chain_id=42161,
        dst_chain_token_out="0xaf",
        dst_chain_token_out_recipient="0xRECIPIENT",
        sender_address="0xSENDER",
    )
    assert params["srcChainOrderAuthorityAddress"] == "0xSENDER"
    assert params["dstChainOrderAuthorityAddress"] == "0xRECIPIENT"


def test_optional_params_are_omitted_when_none() -> None:
    params = build_create_order_params(
        src_chain_id=8453,
        src_chain_token_in="0x83",
        src_chain_token_in_amount="10000000",
        dst_chain_id=42161,
        dst_chain_token_out="0xaf",
        dst_chain_token_out_recipient="0xd8",
        sender_address="0xd8",
    )
    assert "referralCode" not in params
    assert "affiliateFeePercent" not in params
