"""SQLite state repository — current state in one file, no container to run.

Chosen when durability matters and infrastructure does not: a single-process service, a CLI, a
worker, or a demo that must survive a restart.

**SQLite serialises writers**, so the compare-and-swap below holds — the conditional statement is
the whole of the check — but it never genuinely races, and cannot prove that two processes deciding
at once produce exactly one winner. Prove that on Postgres: `make test-integration` there races two
independent connections at one version and requires exactly one save.

`sqlite3` is the standard library, so this adapter adds no dependency. The schema ships with the
adapter rather than as a migration, as the event store's does: an embedded database is created by
the process that opens it. It is the same table the Postgres migration creates, because two
spellings of one schema drift and nothing notices.
"""

from __future__ import annotations

import json
import sqlite3

from delivery_starter.application.ports.repository import (
    NO_STATE,
    Repository,
    Saved,
    SaveResult,
    State,
    VersionConflict,
    VersionedState,
    assert_write,
)

SCHEMA = """
  CREATE TABLE IF NOT EXISTS states (
    id      TEXT    PRIMARY KEY,
    version INTEGER NOT NULL CHECK (version >= 0),
    state   TEXT    NOT NULL
  );
"""


class SqliteRepository(Repository):
    def __init__(self, location: str) -> None:
        # `isolation_level=None` for the reason the event store gives: each save is one statement
        # and commits itself, and the driver's implicit transactions are not wanted around it.
        self._connection = sqlite3.connect(location, isolation_level=None)
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.executescript(SCHEMA)

    def close(self) -> None:
        self._connection.close()

    def load(self, id: str) -> VersionedState | None:
        row = self._connection.execute(
            "SELECT version, state FROM states WHERE id = ?", (id,)
        ).fetchone()
        if row is None:
            return None
        return VersionedState(id=id, version=int(row[0]), state=json.loads(row[1]))

    def save(self, id: str, expected_version: int, state: State) -> SaveResult:
        assert_write(id, expected_version, state)
        text = json.dumps(state, allow_nan=False)
        # One conditional statement either way, so the check and the write cannot be separated:
        # an insert that does nothing when the row exists, or an update that does nothing unless
        # the row is still at the version the caller read.
        if expected_version == NO_STATE:
            changed = self._connection.execute(
                "INSERT INTO states (id, version, state) VALUES (?, 0, ?) "
                "ON CONFLICT (id) DO NOTHING",
                (id, text),
            ).rowcount
        else:
            changed = self._connection.execute(
                "UPDATE states SET state = ?, version = version + 1 WHERE id = ? AND version = ?",
                (text, id, expected_version),
            ).rowcount
        if changed == 1:
            return Saved(expected_version + 1)
        row = self._connection.execute("SELECT version FROM states WHERE id = ?", (id,)).fetchone()
        return VersionConflict(NO_STATE if row is None else int(row[0]))

    def head(self) -> int:
        return int(self._connection.execute("SELECT count(*) FROM states").fetchone()[0])


def open_sqlite_repository(location: str) -> SqliteRepository:
    """Open (or create) a SQLite-backed repository at a file path, or `':memory:'` for one that
    exists only as long as the process — which is what the contract suite uses."""
    return SqliteRepository(location)
