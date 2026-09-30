"""Python's service-layout answers: which committed asset lands where under a service, per feature.

The other half of `python.py`'s `LANGUAGE`, apart for the reason the tables it came from were apart from
`backing_services.py`: most of the bytes and none of the behaviour, and `python.py` has no room left under the line
budget. `ANSWERS` is this backend's, keyed by the member constants, and `LANGUAGE` takes it whole.

Sources are relative to `assets/backing-services/python/`, and a `../` reaches the material shared between
backends. Core merges the two sides feature by feature (`backing_services.service_layout`).
"""
from __future__ import annotations

from typing import Any

from ... import registry as protocol
from ..flag_route import EntryWiring
from ..flags import FlagReader

# The write side: the event port, the adapters behind it, their contract suites and the migrations, and each
# transport's and identity provider's own files.
# Emitted under the template package name; `language_files` renames the directory after the project
# and rewrites the imports, which is why every path here says `delivery_starter`.
WRITE_SIDE: dict[str, dict[str, str]] = {
    "memory": {
        "src/delivery_starter/application/ports/events.py": "events.py",
        "src/delivery_starter/adapters/driven/event_store_memory.py": "event_store_memory.py",
        "tests/conftest.py": "tests/conftest.py",
        "tests/contract/event_store_contract.py": "tests/event_store_contract.py",
        "tests/contract/test_event_store_memory.py": "tests/test_event_store_memory.py",
    },
    "sqlite": {
        "src/delivery_starter/adapters/driven/event_store_sqlite.py": "event_store_sqlite.py",
        "tests/contract/test_event_store_sqlite.py": "tests/test_event_store_sqlite.py",
    },
    "postgres": {
        "src/delivery_starter/adapters/driven/event_store_postgres.py": "event_store_postgres.py",
        "tests/integration/test_event_store_postgres.py": "tests/test_event_store_postgres.py",
        "migrations/apply.py": "migrations_apply.py",
        "migrations/001_events.sql": "../sql/001_events.sql",
        "migrations/002_events_append_only.sql": "../sql/002_events_append_only.sql",
    },
    "fastapi": {
        "src/delivery_starter/adapters/driving/http/app.py": "http_app.py",
        "src/delivery_starter/main.py": "main.py",
        "src/delivery_starter/logging_setup.py": "logging_setup.py",
        # The environment's one model. Under the transport rather than beside the store because
        # the composition root is what reads it: a project with `--http none` has no process of
        # its own to configure.
        "src/delivery_starter/settings.py": "settings.py",
        # The SDK's wiring, under the transport for the same reason: a span per request is
        # the one thing only a transport can produce.
        "src/delivery_starter/tracing.py": "tracing.py",
        # The published document, written from the app rather than beside it. A second entry point,
        # because it builds the app exactly as `main` does and then binds nothing at all.
        "src/delivery_starter/openapi.py": "openapi_export.py",
        "tests/edge/test_http_app.py": "tests/test_http_app.py",
        "tests/test_logging_setup.py": "tests/test_logging_setup.py",
        "tests/test_settings.py": "tests/test_settings.py",
        "tests/test_tracing.py": "tests/test_tracing.py",
    },
    "keycloak": {
        "src/delivery_starter/adapters/driving/http/auth/oidc_keycloak.py": "oidc_keycloak.py",
        "tests/auth/test_oidc_keycloak.py": "tests/test_oidc_keycloak.py",
    },
    "users-keycloak": {
        "src/delivery_starter/adapters/driving/http/users/oidc_keycloak.py": "users_oidc_keycloak.py",
        "tests/users/test_users_oidc_keycloak.py": "tests/test_users_oidc_keycloak.py",
    },
}

# The read side: the checkpoint port and its adapters, the catch-up runner, and the migrations that create the
# checkpoint table and the tag index. Every backend covers the same ground (`docs/backend-obligations.md` §3).
# Emitted under the template package name; `language_files` renames the directory after the
# project and rewrites the imports, which is why every path here says `delivery_starter`.
READ_SIDE: dict[str, dict[str, str]] = {
    "memory": {
        # The timer that drives an async projection: a FastAPI lifespan, so the framework starts
        # it with the app and stops it with the app — and shutdown waits for the pass in flight
        # rather than killing it mid-transaction. Beside the read side, and importing FastAPI
        # nowhere, for the same reason as its TypeScript sibling: a project can have a store and
        # no HTTP adapter at all.
        "src/delivery_starter/projections_lifespan.py": "projections_lifespan.py",
        "tests/contract/test_projections_lifespan.py": "tests/test_projections_lifespan.py",
        "src/delivery_starter/application/ports/read_models.py": "read_models.py",
        "src/delivery_starter/projections.py": "projections.py",
        "src/delivery_starter/adapters/driven/checkpoint_store_memory.py": "checkpoint_store_memory.py",
        "tests/contract/checkpoint_store_contract.py": "tests/checkpoint_store_contract.py",
        "tests/contract/test_checkpoint_store_memory.py": "tests/test_checkpoint_store_memory.py",
        # The runner has no I/O of its own, so its suite runs whatever the store is — which is
        # why it is here under the feature every project has rather than beside an adapter.
        "tests/contract/test_projections.py": "tests/test_projections.py",
    },
    "sqlite": {
        "src/delivery_starter/adapters/driven/checkpoint_store_sqlite.py": "checkpoint_store_sqlite.py",
        "tests/contract/test_checkpoint_store_sqlite.py": "tests/test_checkpoint_store_sqlite.py",
    },
    "postgres": {
        "src/delivery_starter/adapters/driven/checkpoint_store_postgres.py": "checkpoint_store_postgres.py",
        "tests/integration/test_checkpoint_store_postgres.py": "tests/test_checkpoint_store_postgres.py",
        "migrations/003_projection_checkpoints.sql": "../sql/003_projection_checkpoints.sql",
        "migrations/004_event_tags.sql": "../sql/004_event_tags.sql",
    },
}

# Where this backend's feature-flag reader is committed, where it lands in a service, and how a slice asks
# it. Emitted only under a managed target (`flags.flag_reader`).
READER = FlagReader(
    tree="python/flags",
    source="src/delivery_starter/flags.py",
    tests="tests/test_flags.py",
    call='flag_enabled("checkout-v2")',
)

# How the flag source is wired into this backend's entry point, keyed by the HTTP option whose app takes it
# (`flag_route.wire_entry`). No `flag_resource`: this backend's transports are handed the source, and
# discover no route.
# The placeholder sits where this line *sorts* in `main.py`'s import block rather than at the end of
# it: ruff's isort rule is part of a generated Python project's own lint, and a block that ends with
# `.flags` after `.logging_setup` is I001 — a project that fails its first `make lint` for a reason
# nothing it can see put there.
# `uvicorn.run` wraps `build_app`, so that call already spans lines and carries a trailing comma —
# which is `ruff format`'s instruction to give every argument a line of its own. An argument appended
# beside the one before it is reformatted, and a generated project's `make lint` runs the formatter in
# check mode, so it fails there. Hence `argument_line` and no `argument`: `openapi_export.py` builds
# the same app on one line and takes the fragment instead.
WIRING = {
    "fastapi": EntryWiring(
        entry="src/delivery_starter/main.py",
        line="from .flags import default_source",
        argument=", default_source()",
        argument_line="            default_source(),",
    ),
}

ANSWERS: dict[protocol.Member[Any], object] = {
    protocol.WRITE_SIDE_FILES: WRITE_SIDE,
    protocol.READ_SIDE_FILES: READ_SIDE,
    protocol.FLAG_READER: READER,
    protocol.ENTRY_WIRING: WIRING,
    protocol.FLAG_RESOURCE: {},
}
