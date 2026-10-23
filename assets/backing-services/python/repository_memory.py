"""In-memory state repository.

For a quickstart with no infrastructure, and for the contract suite `make verify` runs with nothing
installed. It satisfies the port's contract — the compare-and-swap included, under one lock, so two
threads in one process cannot both win — but it proves nothing about two *processes*: that guarantee
lives in a real store's single conditional statement, and `make test-integration` is where it is
proved on Postgres.

Every row is copied in and copied out through JSON, so a caller that edits the mapping it saved, or
the one it loaded, changes nothing stored — which is what every other adapter does by construction.

Data is lost when the process ends. Never production.
"""

from __future__ import annotations

import json
import threading

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


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        # The stored form is the JSON text, so a load can never hand out a reference to it.
        self._rows: dict[str, tuple[int, str]] = {}
        self._lock = threading.Lock()

    def load(self, id: str) -> VersionedState | None:
        with self._lock:
            row = self._rows.get(id)
        if row is None:
            return None
        version, text = row
        return VersionedState(id=id, version=version, state=json.loads(text))

    def save(self, id: str, expected_version: int, state: State) -> SaveResult:
        assert_write(id, expected_version, state)
        text = json.dumps(state, allow_nan=False)
        with self._lock:
            actual = self._rows.get(id, (NO_STATE, ""))[0]
            if actual != expected_version:
                return VersionConflict(actual)
            self._rows[id] = (actual + 1, text)
            return Saved(actual + 1)

    def head(self) -> int:
        with self._lock:
            return len(self._rows)


def create_in_memory_repository() -> InMemoryRepository:
    """A fresh, empty repository that lives as long as the process."""
    return InMemoryRepository()
