"""Tests for the constants module (chain ids, sentinels, terminal statuses)."""

from debridge import constants


def test_default_base_url() -> None:
    assert constants.DEFAULT_BASE_URL == "https://dln.debridge.finance/v1.0"


def test_known_chain_ids() -> None:
    assert constants.ChainId.ETHEREUM.value == 1
    assert constants.ChainId.BASE.value == 8453
    assert constants.ChainId.ARBITRUM.value == 42161
    assert constants.ChainId.SOLANA.value == 7565164


def test_native_token_sentinels() -> None:
    assert constants.EVM_NATIVE_TOKEN == "0x0000000000000000000000000000000000000000"
    assert constants.SOLANA_NATIVE_TOKEN == "11111111111111111111111111111111"


def test_terminal_statuses_include_fulfilled_and_cancelled() -> None:
    assert "Fulfilled" in constants.TERMINAL_STATUSES
    assert "Cancelled" in constants.TERMINAL_STATUSES
    # An in-flight state must NOT be terminal.
    assert "Created" not in constants.TERMINAL_STATUSES
