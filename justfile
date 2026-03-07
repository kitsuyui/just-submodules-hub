default_owners := "kitsuyui,gitignore-in"
default_visibility := "all"

import "just/index.just"

test:
  uv run pytest tests/unit tests/integration

test-unit:
  uv run pytest tests/unit

test-integration:
  uv run pytest tests/integration

test-e2e-real:
  RUN_REAL_E2E=1 uv run pytest -m real_e2e tests/e2e

default:
  @just --list
