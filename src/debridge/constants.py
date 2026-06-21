"""Constants for the deBridge DLN API: base URL, chain ids, sentinels, statuses."""

from __future__ import annotations

from enum import IntEnum
from typing import FrozenSet

#: Default DLN API base URL. Override via ``DebridgeClient(base_url=...)``.
DEFAULT_BASE_URL = "https://dln.debridge.finance/v1.0"

#: Sentinel addresses for the native gas token on each VM family.
EVM_NATIVE_TOKEN = "0x0000000000000000000000000000000000000000"
SOLANA_NATIVE_TOKEN = "11111111111111111111111111111111"


class ChainId(IntEnum):
    """deBridge internal chain ids (note: differ from native chain ids for some
    chains, e.g. Solana). Values verified live against ``/supported-chains-info``.
    """

    ETHEREUM = 1
    OPTIMISM = 10
    BSC = 56
    POLYGON = 137
    BASE = 8453
    ARBITRUM = 42161
    AVALANCHE = 43114
    LINEA = 59144
    SOLANA = 7565164


#: Order statuses that ``poll_status`` treats as final by default. ``Fulfilled``
#: is the success terminal for the taker side; the ``*Cancel``/``*Unlock``
#: claimed states are final on the giver side. Intermediate states such as
#: ``Created``, ``SentUnlock`` and ``SentOrderCancel`` are deliberately excluded.
TERMINAL_STATUSES: FrozenSet[str] = frozenset(
    {
        "Fulfilled",
        "ClaimedUnlock",
        "Cancelled",
        "OrderCancelled",
        "ClaimedOrderCancel",
    }
)
