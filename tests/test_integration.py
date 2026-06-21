"""Live integration test against the real deBridge API.

Marked ``integration`` and deselected by default (see pyproject ``addopts``).
Run explicitly with::

    pytest -m integration
"""

import pytest

from debridge import DebridgeClient
from debridge.constants import ChainId

pytestmark = pytest.mark.integration


def test_live_supported_chains() -> None:
    with DebridgeClient() as client:
        resp = client.get_supported_chains()
    names = {c.chain_name for c in resp.chains}
    # These have been stable on mainnet for a long time.
    assert "Ethereum" in names
    assert "Solana" in names
    assert len(resp.chains) >= 10
    solana = next(c for c in resp.chains if c.chain_name == "Solana")
    assert solana.chain_id == 7565164


def test_live_chains_are_all_in_chain_id_enum() -> None:
    # The ChainId enum must stay in sync with what the API actually returns:
    # every live chain id must have a corresponding enum member.
    with DebridgeClient() as client:
        resp = client.get_supported_chains()
    live_ids = {c.chain_id for c in resp.chains}
    enum_ids = {member.value for member in ChainId}
    missing = live_ids - enum_ids
    assert not missing, f"ChainId enum is missing live chain ids: {sorted(missing)}"
