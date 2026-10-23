"""One contract, run against every state repository adapter.

The in-memory and SQLite adapters run it in `make test`; Postgres runs it in `make
test-integration`. No adapter gets its own version of the rule: two adapters that pass different
tests are two ports wearing one name.

A mixin rather than a fixture, as the event-store contract is: each adapter's module subclasses this
and supplies `make_repository`, and the name does not start with `Test`, so this file contributes no
tests of its own. Every test works under a freshly made id, so the suite can share a real table with
every earlier run and assert only about its own rows.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

import pytest

from delivery_starter.application.ports.repository import (
    NO_STATE,
    Repository,
    Saved,
    VersionConflict,
    VersionedState,
)


class RepositoryContract:
    def make_repository(self) -> Repository:
        raise NotImplementedError

    @pytest.fixture
    def repository(self) -> Repository:
        return self.make_repository()

    @pytest.fixture
    def row(self) -> str:
        return f"row-{uuid.uuid4()}"

    def test_reads_an_unknown_row_as_absent(self, repository: Repository, row: str) -> None:
        assert repository.load(row) is None

    def test_creates_at_no_state_and_updates_only_at_the_version_it_read(
        self, repository: Repository, row: str
    ) -> None:
        assert repository.save(row, NO_STATE, {"status": "draft"}) == Saved(0)
        assert repository.save(row, 0, {"status": "confirmed"}) == Saved(1)
        assert repository.load(row) == VersionedState(row, 1, {"status": "confirmed"})

    def test_refuses_a_stale_decision_and_leaves_the_winning_state_alone(
        self, repository: Repository, row: str
    ) -> None:
        repository.save(row, NO_STATE, {"status": "draft"})
        repository.save(row, 0, {"status": "confirmed"})
        assert repository.save(row, 0, {"status": "cancelled"}) == VersionConflict(1)
        loaded = repository.load(row)
        assert loaded is not None and loaded.state == {"status": "confirmed"}

    def test_cannot_create_a_row_that_exists(self, repository: Repository, row: str) -> None:
        repository.save(row, NO_STATE, {"writer": "first"})
        assert repository.save(row, NO_STATE, {"writer": "second"}) == VersionConflict(0)

    def test_cannot_manufacture_a_missing_row_from_a_later_version(
        self, repository: Repository, row: str
    ) -> None:
        assert repository.save(row, 0, {"status": "confirmed"}) == VersionConflict(NO_STATE)
        assert repository.load(row) is None

    def test_rejects_values_that_would_change_when_stored_as_json(
        self, repository: Repository, row: str
    ) -> None:
        for state in (
            {"bad": math.nan},
            {"bad": datetime.now(UTC)},
            {"bad": (1, 2)},
            {"bad": {1: "integer key"}},
        ):
            with pytest.raises(ValueError, match="JSON"):
                repository.save(row, NO_STATE, state)
            assert repository.load(row) is None

    def test_rejects_a_write_that_names_no_row_or_no_version_it_read(
        self, repository: Repository
    ) -> None:
        with pytest.raises(ValueError, match="id"):
            repository.save(" ", NO_STATE, {})
        with pytest.raises(ValueError, match="expected_version"):
            repository.save(f"row-{uuid.uuid4()}", -2, {})

    def test_does_not_share_mutable_objects_with_the_caller(
        self, repository: Repository, row: str
    ) -> None:
        state = {"nested": {"count": 1}}
        repository.save(row, NO_STATE, state)
        state["nested"]["count"] = 10
        loaded = repository.load(row)
        assert loaded is not None and loaded.state == {"nested": {"count": 1}}

    def test_counts_its_rows_for_the_readiness_probe(
        self, repository: Repository, row: str
    ) -> None:
        before = repository.head()
        repository.save(row, NO_STATE, {})
        assert repository.head() == before + 1
