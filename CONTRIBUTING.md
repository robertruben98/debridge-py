# Contributing to debridge-py

Thanks for your interest in improving `debridge-py`! This guide covers the local
setup and the quality bar every change must meet.

## Development setup

The project targets **Python 3.9+** and is developed against a real 3.9
interpreter to catch version-specific issues early.

```bash
git clone https://github.com/robertruben98/debridge-py
cd debridge-py
uv venv --python 3.9 && source .venv/bin/activate
uv pip install -e ".[dev]"
```

(If you don't use `uv`, a plain `python -m venv .venv && pip install -e ".[dev]"`
works too.)

## Workflow

1. Branch off `main` (e.g. `feat/...`, `fix/...`, `docs/...`).
2. **Write tests first.** This project follows test-driven development: add a
   failing test, then the minimal code to pass it. Unit tests must not hit the
   network — mock HTTP with `respx`. Live calls go in tests marked
   `@pytest.mark.integration`, which are deselected by default.
3. Keep changes focused and small. Commit messages use the `feat:` / `fix:` /
   `chore:` / `docs:` style; do not add AI co-author trailers.
4. Open a pull request against `main`. CI (lint + the 3.9–3.13 test matrix) must
   be green before review.

## Quality gates

All of these must pass locally before you push:

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy                    # strict type checking
pytest -q               # unit tests (integration deselected)
```

To run the single live integration test against the real API:

```bash
pytest -m integration
```

## Code conventions

- Public API is exported from `debridge/__init__.py`; keep `__all__` in sync.
- Models live in `debridge/models.py` (pydantic v2, camelCase API aliases,
  `extra="allow"` for forward compatibility). Addresses and amounts are strings
  so the same models work for EVM and Solana.
- Annotations stay 3.9-compatible: use `typing.Optional`/`List`/`Dict`, not PEP
  604 `X | None` or bare `list[...]`, in anything pydantic evaluates at runtime.
- Document new public methods and models with Google-style docstrings
  (`Args`/`Returns`/`Raises`) and `Field(description=...)`.

## Releasing

Maintainers bump the version in `pyproject.toml`, move entries from
`Unreleased` into a new section in `CHANGELOG.md`, tag `vX.Y.Z`, and let CI build
and publish. `uvx twine check dist/*` must pass on the built artifacts.
