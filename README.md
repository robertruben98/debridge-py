# debridge-py

[![CI](https://github.com/robertruben98/debridge-py/actions/workflows/ci.yml/badge.svg)](https://github.com/robertruben98/debridge-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/debridge-py.svg)](https://pypi.org/project/debridge-py/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://robertruben98.github.io/debridge-py/)
[![Python versions](https://img.shields.io/pypi/pyversions/debridge-py.svg)](https://pypi.org/project/debridge-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/robertruben98/debridge-py/blob/main/LICENSE)

Typed Python client for the [deBridge DLN](https://docs.debridge.com/) cross-chain
swap/order API. Works across EVM chains and Solana (19+ chains), sync **and** async,
with full type hints (`py.typed`), built on `httpx` + `pydantic v2`.

The client covers the public, no-auth data endpoints needed to quote and track
cross-chain orders. Signing and broadcasting the returned transaction is left to
you (optionally with the `[exec]` extra: `web3.py` for EVM, `solders` for Solana).

## Install

```bash
pip install debridge-py
# optional signing helpers:
pip install "debridge-py[exec]"
```

## Quickstart

```python
from debridge import DebridgeClient
from debridge.constants import ChainId

with DebridgeClient() as client:
    # 1. discover supported chains
    chains = client.get_supported_chains()

    # 2. quote + build a cross-chain order (10 USDC Base -> USDC Arbitrum)
    order = client.create_order(
        src_chain_id=ChainId.BASE,
        src_chain_token_in="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        src_chain_token_in_amount="10000000",  # 10 USDC (6 decimals)
        dst_chain_id=ChainId.ARBITRUM,
        dst_chain_token_out="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        dst_chain_token_out_amount="auto",  # API quotes the output
        dst_chain_token_out_recipient="0xYourRecipient",
        sender_address="0xYourSender",
    )
    print(order.estimation.dst_chain_token_out.amount)  # estimated output
    print(order.tx.to, order.tx.value, order.tx.data)  # tx to sign & send

    # 3. after broadcasting order.tx, poll until the order settles
    final = client.poll_status(order.order_id, interval=5, timeout=600)
    print(final.status)  # e.g. "Fulfilled"
```

### Async

```python
import asyncio
from debridge import AsyncDebridgeClient


async def main():
    async with AsyncDebridgeClient() as client:
        chains = await client.get_supported_chains()
        print(len(chains.chains))


asyncio.run(main())
```

## EVM and Solana

Addresses and amounts are kept as **strings** so the same models represent both
`0x`-hex (EVM) and base58 (Solana) values and amounts beyond 64-bit range. The
returned transaction adapts to the **source** chain:

- EVM source → `order.tx` has `data`, `to`, `value` (an EVM call).
- Solana source → `order.tx` has only `data` (the serialized versioned tx as hex).

Native-token sentinels are exposed as `constants.EVM_NATIVE_TOKEN` and
`constants.SOLANA_NATIVE_TOKEN`.

## API surface

| Method | Endpoint |
| --- | --- |
| `get_supported_chains()` | `GET /supported-chains-info` |
| `get_token_list(chain_id)` | `GET /token-list` |
| `create_order(...)` | `GET /dln/order/create-tx` |
| `get_order_status(order_id)` | `GET /dln/order/{id}/status` |
| `get_order(order_id)` | `GET /dln/order/{id}` |
| `poll_status(order_id, interval, timeout)` | polls status to a terminal state |

Every method exists on both `DebridgeClient` (sync) and `AsyncDebridgeClient`
(async, with `await`). Errors raise `DebridgeAPIError` (a `DebridgeError`),
exposing `.error_id`, `.error_code`, `.message`, `.req_id`, `.status_code` —
including compliance blocks that the API returns with HTTP 200.

## Configuration

```python
DebridgeClient(base_url="https://my-proxy.example/v1.0", timeout=30.0)
```

`base_url` defaults to `https://dln.debridge.finance/v1.0` and can point at any
compatible endpoint.

## Development

```bash
uv venv --python 3.9 && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest            # unit tests (network mocked, integration deselected)
pytest -m integration   # one live test against the real API
ruff check . && ruff format --check .
mypy
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributor workflow and
[CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT — see [LICENSE](LICENSE).
