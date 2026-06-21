"""Live integration test against the real deBridge API.

Marked ``integration`` and deselected by default (see pyproject ``addopts``).
Run explicitly with::

    pytest -m integration
"""

import pytest

from debridge import DebridgeClient

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
