"""The Python family's rows for the generated pruning script (`prune_rows`, S06).

Written into a project's `scripts/backing-services.py` when it has a Python service, and read by the factory's
own pruner. The shape is fixed in `specs/001-slipwai-2-language-addons/contracts/backend-protocol.md`. The paths
glob because a Python service's package directory is named after the project.
"""
from __future__ import annotations

PRUNE_ROWS = {
    "marked_files": ("src/*/settings.py", "src/*/main.py"),
    "owned_files": {
        "sqlite": (
            "src/*/adapters/driven/event_store_sqlite.py",
            "src/*/adapters/driven/checkpoint_store_sqlite.py",
            "tests/contract/test_event_store_sqlite.py",
            "tests/contract/test_checkpoint_store_sqlite.py",
        ),
        "postgres": (
            "src/*/adapters/driven/event_store_postgres.py",
            "src/*/adapters/driven/checkpoint_store_postgres.py",
            "migrations/apply.py",
            "migrations/001_events.sql",
            "migrations/002_events_append_only.sql",
            "migrations/003_projection_checkpoints.sql",
            "migrations/004_event_tags.sql",
            "tests/integration/test_event_store_postgres.py",
            "tests/integration/test_checkpoint_store_postgres.py",
        ),
        "fastapi": (
            "src/*/adapters/driving/http/app.py",
            "src/*/main.py",
            "src/*/logging_setup.py",
            "src/*/settings.py",
            "src/*/tracing.py",
            "src/*/openapi.py",
            "openapi.json",
            "tests/edge/test_http_app.py",
            "tests/test_logging_setup.py",
            "tests/test_settings.py",
            "tests/test_tracing.py",
        ),
        "keycloak": ("src/*/adapters/driving/http/auth/oidc_keycloak.py", "tests/auth/test_oidc_keycloak.py"),
        "users-keycloak": (
            "src/*/adapters/driving/http/users/oidc_keycloak.py",
            "tests/users/test_users_oidc_keycloak.py",
        ),
    },
    # Dropped from `pyproject.toml`'s two arrays by distribution name, then re-locked with `uv lock`.
    "package_edits": {
        "postgres": {"packages": ("psycopg[binary]",), "scripts": ()},
        # The framework, its server, the client its own edge suite drives it with, and the settings model the
        # composition root checks the environment against: all arrive with the transport and nothing else in the
        # service imports any of them.
        "fastapi": {
            "packages": (
                "fastapi",
                "uvicorn",
                "httpx",
                "opentelemetry-api",
                "opentelemetry-exporter-otlp-proto-http",
                "opentelemetry-instrumentation-fastapi",
                "opentelemetry-sdk",
                "pydantic-settings",
            ),
            "scripts": (),
        },
    },
    "manifest": "pyproject.toml",
}
