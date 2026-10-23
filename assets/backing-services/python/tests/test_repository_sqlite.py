"""The repository contract, against SQLite, plus the one thing only a file can prove.

`:memory:` for the contract, so each case starts from a fresh database. That the state survives the
process needs a real file, and is below. Runs in `make verify`, with nothing to start or migrate.
"""

from __future__ import annotations

from pathlib import Path

from contract.repository_contract import RepositoryContract

from delivery_starter.adapters.driven.repository_sqlite import open_sqlite_repository
from delivery_starter.application.ports.repository import (
    NO_STATE,
    Repository,
    Saved,
    VersionedState,
)


class TestSqliteRepository(RepositoryContract):
    def make_repository(self) -> Repository:
        return open_sqlite_repository(":memory:")


def test_keeps_the_state_and_its_version_across_a_close_and_reopen(tmp_path: Path) -> None:
    location = str(tmp_path / "states.sqlite3")
    first = open_sqlite_repository(location)
    first.save("order-1", NO_STATE, {"status": "placed"})
    first.close()

    reopened = open_sqlite_repository(location)
    try:
        assert reopened.load("order-1") == VersionedState("order-1", 0, {"status": "placed"})
        assert reopened.save("order-1", 0, {"status": "paid"}) == Saved(1)
    finally:
        reopened.close()
