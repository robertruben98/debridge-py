# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

Initial release. Not yet published to PyPI.

### Added

- `DebridgeClient` (sync) and `AsyncDebridgeClient` (async) for the deBridge DLN
  API, built on `httpx`, usable as (async) context managers.
- Endpoints: `get_supported_chains`, `get_token_list`, `create_order`
  (`/dln/order/create-tx`), `get_order_status`, `get_order`, and a `poll_status`
  helper that polls an order to a terminal state.
- Support for both EVM and Solana: addresses and amounts are strings, and the
  returned `Transaction` carries `to`/`value` for EVM sources and `data`-only
  for Solana sources.
- Typed pydantic v2 models with forward-compatible parsing (`extra="allow"`),
  shipped with `py.typed`.
- `ChainId` enum covering all 19 supported chains, plus native-token sentinels
  and `TERMINAL_STATUSES` in `debridge.constants`.
- `DebridgeError` / `DebridgeAPIError`, which surface both non-2xx responses and
  HTTP-200 error bodies (e.g. compliance blocks).
- Optional `[exec]` extra (`web3`, `solders`) for signing/broadcasting.
- Sync and async usage examples, README quickstart, and GitHub Actions CI
  (lint + test matrix on Python 3.9–3.13).

[Unreleased]: https://github.com/robertruben98/debridge-py/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/robertruben98/debridge-py/releases/tag/v0.1.0
