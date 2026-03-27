# E2E Test Suite

This folder contains Playwright end-to-end tests for the Streamlit UI.

## Scope

- Navigation smoke checks
- Calculator interaction flow
- Custom parlay flow
- Bankroll form flow
- Live center interaction

## Local Run

```bash
./.venv/bin/pytest tests/e2e/test_navigation.py -v --headed
```

## Full E2E Run

```bash
./.venv/bin/pytest tests/e2e/ -v
```

## Failure Artifacts

On test failure, screenshots are written to `tests/e2e/artifacts/`.

## Notes

- The fixture in `conftest.py` starts Streamlit on `127.0.0.1:8504` for tests.
- Browser viewport is fixed at `1440x900` for deterministic rendering.
