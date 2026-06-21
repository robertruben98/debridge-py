"""Tests for the constants module (chain ids, sentinels, terminal statuses)."""

from debridge import constants


def test_default_base_url() -> None:
    assert constants.DEFAULT_BASE_URL == "https://dln.debridge.finance/v1.0"


def test_known_chain_ids() -> None:
    assert constants.ChainId.ETHEREUM.value == 1
    assert constants.ChainId.BASE.value == 8453
    assert constants.ChainId.ARBITRUM.value == 42161
    assert constants.ChainId.SOLANA.value == 7565164


def test_chain_id_enum_covers_all_supported_chains() -> None:
    # The full set returned live by GET /supported-chains-info (19 chains).
    # The enum must enumerate every one of them, including the special
    # Solana id (7565164) and the 1e8-offset ids for non-EVM/L2 chains.
    expected = {
        1,  # Ethereum
        10,  # Optimism
        56,  # BSC
        137,  # Polygon
        8453,  # Base
        42161,  # Arbitrum
        43114,  # Avalanche
        59144,  # Linea
        7565164,  # Solana
        100000009,  # Flow
        100000013,  # Story
        100000019,  # Cronos
        100000022,  # HyperEVM
        100000023,  # Mantle
        100000026,  # Tron
        100000027,  # Sei
        100000029,  # Injective
        100000030,  # Monad
        100000031,  # Megaeth
    }
    actual = {member.value for member in constants.ChainId}
    assert actual == expected
    assert len(constants.ChainId) == 19


def test_native_token_sentinels() -> None:
    assert constants.EVM_NATIVE_TOKEN == "0x0000000000000000000000000000000000000000"
    assert constants.SOLANA_NATIVE_TOKEN == "11111111111111111111111111111111"


def test_terminal_statuses_include_fulfilled_and_cancelled() -> None:
    assert "Fulfilled" in constants.TERMINAL_STATUSES
    assert "Cancelled" in constants.TERMINAL_STATUSES
    # An in-flight state must NOT be terminal.
    assert "Created" not in constants.TERMINAL_STATUSES
