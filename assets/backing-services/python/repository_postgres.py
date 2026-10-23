"""Postgres state repository — the store a state-stored service ships on.

The compare-and-swap is **one SQL statement**: an insert that does nothing when the row exists, or
an update that compares and increments the version in the same `WHERE`. Postgres takes the row lock
for that statement, so two connections saving at one version cannot both match it — one updates the
row, and the other finds it already moved and changes nothing. No `SELECT ... FOR UPDATE`, no
isolation level to remember: there is no gap between the check and the write for anything to fall
into.

The table is created by `migrations/001_states.sql`, applied by `make migrate`, and its `CHECK` says
the state is a JSON object — the same rule the port enforces, held where the next process to open
the database will meet it too.

The driver is imported only by a process that talks to a database, for the reason the event store's
adapter gives.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:  # pragma: no cover - typing only
    from psycopg import Connection


class PostgresRepository(Repository):
    def __init__(self, connection: Connection[Any]) -> None:
        self._connection = connection

    def load(self, id: str) -> VersionedState | None:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT version, state FROM states WHERE id = %s", (id,))
            row = cursor.fetchone()
        self._connection.commit()
        if row is None:
            return None
        state = row[1] if isinstance(row[1], dict) else json.loads(row[1])
        return VersionedState(id=id, version=int(row[0]), state=state)

    def save(self, id: str, expected_version: int, state: State) -> SaveResult:
        assert_write(id, expected_version, state)
        text = json.dumps(state, allow_nan=False)
        with self._connection.cursor() as cursor:
            if expected_version == NO_STATE:
                cursor.execute(
                    "INSERT INTO states (id, version, state) VALUES (%s, 0, %s::jsonb) "
                    "ON CONFLICT (id) DO NOTHING RETURNING version",
                    (id, text),
                )
            else:
                cursor.execute(
                    "UPDATE states SET state = %s::jsonb, version = version + 1 "
                    "WHERE id = %s AND version = %s RETURNING version",
                    (text, id, expected_version),
                )
            saved = cursor.fetchone()
            if saved is None:
                cursor.execute("SELECT version FROM states WHERE id = %s", (id,))
                found = cursor.fetchone()
        self._connection.commit()
        if saved is not None:
            return Saved(int(saved[0]))
        return VersionConflict(NO_STATE if found is None else int(found[0]))

    def head(self) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM states")
            row = cursor.fetchone()
        self._connection.commit()
        return 0 if row is None else int(row[0])


def create_postgres_repository(connection: Connection[Any]) -> PostgresRepository:
    """A repository over one open connection, which this adapter commits after every statement."""
    return PostgresRepository(connection)
