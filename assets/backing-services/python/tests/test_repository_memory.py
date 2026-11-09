"""The repository contract, against the fake, plus the one race a single process can run.

This runs in `make verify` and needs no Docker. `make test-integration` runs the same contract
against Postgres, with independent connections, which is the race that matters in production.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

from contract.repository_contract import RepositoryContract

from delivery_starter.adapters.driven.repository_memory import (
    create_in_memory_repository,
)
from delivery_starter.application.ports.repository import (
    NO_STATE,
    Repository,
    Saved,
)


class TestInMemoryRepository(RepositoryContract):
    def make_repository(self) -> Repository:
        return create_in_memory_repository()


def test_gives_exactly_one_of_many_threads_saving_at_one_version_the_win() -> None:
    repository = create_in_memory_repository()
    row = f"race-{uuid.uuid4()}"
    repository.save(row, NO_STATE, {"writer": "original"})
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda n: repository.save(row, 0, {"writer": n}), range(8)))
    assert [result for result in results if isinstance(result, Saved)] == [Saved(1)]
