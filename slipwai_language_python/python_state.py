"""The state-stored rung: which files a service answered `write-model: state` is given, and how its entry
point opens the repository instead of the event store.

The rows are the `state` block of `python_layout.WRITE_SIDE`, keyed by feature the way the event-sourced rows
above it are, because the rung does not settle which store was chosen — the persistence axis did. What it
settles is what the store is asked to hold: one current row per id with a version, where the other rung
keeps a log. So the event port, its adapters, the checkpoint store and the catch-up runner are not here, and
the repository port and its adapters are; the transport and identity rows are the same files on either rung.

The composition root is the other half. Core's `wire_store` writes the event store's opener from this
backend's `entry_store` answer, and that answer is about the log. A state-stored service opens its
repository through the same placeholders, under the same three rules `composition.py` sets out — one store,
opened once by the entry point; the answer in its own marked region; nothing connecting while the process
starts — so the repository's opener is the event store's, renamed, and wired here rather than by teaching
the keel which Python adapter a repository is.
"""
from __future__ import annotations

from dataclasses import replace

from slipwai.project.composition import (
    APP_IMPORTS,
    SETTINGS_IMPORTS,
    STORE_ARGUMENT,
    STORE_IMPORT,
    STORE_OPEN,
)
from slipwai.project.entry_stores import FEATURE, EntryStore
from slipwai.selection import Selection

# Sources are relative to `assets/backing-services/python/`, as every other row's are.
STATE_WRITE: dict[str, dict[str, str]] = {
    "memory": {
        "src/delivery_starter/application/ports/repository.py": "repository.py",
        "src/delivery_starter/adapters/driven/repository_memory.py": "repository_memory.py",
        "tests/conftest.py": "tests/conftest.py",
        "tests/contract/repository_contract.py": "tests/repository_contract.py",
        "tests/contract/test_repository_memory.py": "tests/test_repository_memory.py",
    },
    "sqlite": {
        "src/delivery_starter/adapters/driven/repository_sqlite.py": "repository_sqlite.py",
        "tests/contract/test_repository_sqlite.py": "tests/test_repository_sqlite.py",
    },
    "postgres": {
        "src/delivery_starter/adapters/driven/repository_postgres.py": "repository_postgres.py",
        "tests/integration/test_repository_postgres.py": "tests/test_repository_postgres.py",
        "migrations/apply.py": "migrations_apply.py",
        "migrations/001_states.sql": "../sql/001_states.sql",
    },
}

# What the event store's opener says, and what the repository's says in its place. Longest first, so a
# module name is rewritten before the shorter name inside it.
RENAMES = (
    ("create_in_memory_event_store", "create_in_memory_repository"),
    ("create_postgres_event_store", "create_postgres_repository"),
    ("open_sqlite_event_store", "open_sqlite_repository"),
    ("event_store_memory", "repository_memory"),
    ("event_store_sqlite", "repository_sqlite"),
    ("event_store_postgres", "repository_postgres"),
    ("open_event_store", "open_repository"),
    ("event store", "state repository"),
)


def renamed(text: str) -> str:
    """One string of the event store's wiring, saying repository wherever it said event store."""
    for old, new in RENAMES:
        text = text.replace(old, new)
    return text


def state_store(events: EntryStore) -> EntryStore:
    """The repository's entry-point wiring, derived from the event store's so the two cannot drift."""
    return replace(
        events,
        imports={key: renamed(value) for key, value in events.imports.items()},
        open={key: renamed(value) for key, value in events.open.items()},
        argument=renamed(events.argument),
    )


def wire_state(files: dict[str, str], selection: Selection, events: EntryStore) -> dict[str, str]:
    """Resolve the entry point's store placeholders with the repository, in place, as `wire_store` does with
    the event store.

    Only called for a service on the state rung whose persistence axis was asked; a service with no store at
    all — the standard profile — is `wire_store`'s, which removes the placeholders on either rung.
    """
    wiring = state_store(events)
    if wiring.entry not in files:
        return files
    store = selection.feature_of("persistence")
    opened = wiring.open[store].rstrip("\n") + "\n" + wiring.gap
    imported = wiring.imports[store]
    if store is not None:
        opened, imported = opened.replace(FEATURE, store), imported.replace(FEATURE, store)
    content = files[wiring.entry]
    for placeholder, replacement in ((STORE_IMPORT, imported), (STORE_OPEN, opened)):
        content = content.replace(f"{placeholder}\n", replacement)
    content = content.replace(STORE_ARGUMENT, wiring.argument)
    for placeholder, table in ((APP_IMPORTS, wiring.app_imports), (SETTINGS_IMPORTS, wiring.settings_imports)):
        if table is not None:
            content = content.replace(placeholder, table[store])
    # The prose around the placeholders speaks of the store this service keeps, too.
    files[wiring.entry] = renamed(content)
    return files
