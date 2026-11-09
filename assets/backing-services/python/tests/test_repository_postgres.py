"""The state repository against real Postgres.

Deliberately NOT part of `make verify`: the repository gate stays runnable with no infrastructure,
and this is the target that needs a database.

    make services-up migrate test-integration

It runs the same contract the infrastructure-free adapters pass, plus the one thing only a real
store can prove: that independent connections saving at one version — the first insert and an
update alike — produce exactly one winner. The fake serialises its callers under a lock and SQLite
serialises its writers, so neither can genuinely race.
"""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
from contract.repository_contract import RepositoryContract

from delivery_starter.adapters.driven.repository_postgres import (
    create_postgres_repository,
)
from delivery_starter.application.ports.repository import (
    NO_STATE,
    Repository,
    Saved,
    SaveResult,
    VersionConflict,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _connect() -> psycopg.Connection:
    """Open a connection, turning a refused one into the instruction that fixes it."""
    if not DATABASE_URL.strip():
        raise RuntimeError(
            "DATABASE_URL is unset, so there is no database to test against. Run "
            "`make test-integration`, which sets it, after `make services-up migrate`."
        )
    try:
        connection = psycopg.connect(DATABASE_URL)
    except psycopg.OperationalError as error:  # pragma: no cover - environment failure
        raise RuntimeError(
            f"Cannot reach the database at {DATABASE_URL}. Start it and apply the schema "
            "first:  make services-up migrate"
        ) from error
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT 1 FROM states LIMIT 1")
        except psycopg.errors.UndefinedTable as error:  # pragma: no cover - environment
            connection.close()
            raise RuntimeError(
                "The states table does not exist. Apply the schema first:  make services-up migrate"
            ) from error
    connection.commit()
    return connection


class TestPostgresRepository(RepositoryContract):
    """The shared contract, against the real thing."""

    def make_repository(self) -> Repository:
        return create_postgres_repository(_connect())


def test_exactly_one_of_many_independent_connections_wins_the_insert_and_the_update() -> None:
    row = f"race-{uuid.uuid4()}"
    attempts = 8

    def attempt(expected_version: int, index: int) -> SaveResult:
        # One connection per worker: two saves on one connection cannot race, they queue.
        with psycopg.connect(DATABASE_URL) as handle:
            return create_postgres_repository(handle).save(row, expected_version, {"writer": index})

    for expected_version, won in ((NO_STATE, Saved(0)), (0, Saved(1))):
        with ThreadPoolExecutor(max_workers=attempts) as pool:
            results = list(pool.map(lambda n, v=expected_version: attempt(v, n), range(attempts)))
        assert [result for result in results if isinstance(result, Saved)] == [won]
        losers = [result for result in results if not isinstance(result, Saved)]
        assert losers == [VersionConflict(won.version)] * (attempts - 1)

    with psycopg.connect(DATABASE_URL) as handle:
        loaded = create_postgres_repository(handle).load(row)
    assert loaded is not None and loaded.version == 1
