# ADR-0002: SDK installed with `pip install -e` in dev, non-editable in production

- **Status:** accepted
- **Date:** 2026-10-17
- **Task:** D-01 (implementation), D-07 (production image)

## Context

The dashboard needs the SDK from the same commit as the daemon (ADR-0001). During development we
also want SDK edits (e.g. the progress hook, D-43) to be visible immediately. The SDK is a normal
Poetry package (`mosaico-sdk-py/pyproject.toml`, `poetry-core>=2` backend, which supports PEP 660
editable installs). It contains only Python: no Rust, no server.

## Decision

- **Development:** the dashboard uses Poetry for its own dependencies, then the SDK is added to
  the dashboard's `.venv` with `poetry run pip install -e ../mosaico-sdk-py`
  (scripted in `scripts/dev_setup.sh`).
- **Production / Docker:** `pip install ./mosaico-sdk-py` (non-editable) from the same commit.
- `mosaicolabs` is **not** declared in the dashboard's `pyproject.toml`.

## Alternatives considered

- **Poetry path dependency** (`mosaicolabs = { path = "../mosaico-sdk-py", develop = true }`):
  tracked in the lock file, but the editable/non-editable switch for production then requires
  editing `pyproject.toml`; we chose the explicit pip step.
- **PyPI version pin:** not possible for `0.8.0-dev`; reconsider if the dashboard is ever extracted.

## Consequences

- `poetry sync` / `poetry install --sync` would **uninstall** the SDK (it's not in the lock);
  always run `scripts/dev_setup.sh` after syncing.
- Poetry's resolver doesn't see the SDK's dependencies. Keep shared ones (e.g. `pydantic`)
  constrained compatibly, and run `pip check` in CI.
- The SDK still needs a **running mosaicod** to do anything.

## Implementation notes (D-01, 2026-10-17)

- Verified: `pip show mosaicolabs` → `Editable project location: …/mosaico-sdk-py`, version
  `0.8.0.dev0`, matching the daemon's `0.8.0-dev`. `pip check` clean.
- `python = ">=3.10,<4"` is a supported range, same as the SDK, not a pin. Poetry does not
  download Python; the venv uses whichever interpreter Poetry finds (pick one once with
  `poetry env use python3.12`). The Docker image uses 3.12.
- Poetry 2.5.1 locally and in the Dockerfile (the SDK's lock was written by 2.4.1; compatible).
- In the image, the SDK is a regular install in `/opt/venv/lib/python3.12/site-packages`.
