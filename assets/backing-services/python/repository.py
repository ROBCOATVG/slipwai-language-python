"""The state repository port: one current row per id, guarded by the version it was read at.

This is the other rung of the write model. An event-sourced service keeps a log and folds it into
state; a state-stored service keeps the state and nothing behind it. The events the model names are
still contracts — raised after a write has won, for whoever reads them — but they are never
replayed, so there is no log here and no projection to be behind.

What keeps two decisions honest without a log is the **version**. `load` hands back the row with the
version it is at; `save` writes only if the row is still at the version the caller decided against,
and otherwise reports what it found. A conflict is a value, not an exception: contention is
expected, and the caller's next move — reload, decide again — is ordinary control flow.

  * `NO_STATE` is the version of a row that does not exist yet. Saving at it creates the row at
    version 0, and only if nobody else created it first.
  * Every successful save moves the version on by exactly one.
  * A save at any other version than the one stored changes nothing.

State is a JSON object, checked before anything is written. Every adapter stores the same values:
the in-memory fake must not keep a `datetime`, a tuple or a `NaN` that SQLite and Postgres would
refuse or quietly change, because a test that passes on the fake and not on the store is a test
that proved the fake.

Nothing here names SQLite, Postgres, or a vendor. Every adapter under `adapters/driven/` implements
it, and one contract suite runs against all of them. Synchronous for the reason the event-store port
is: both drivers are.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

#: `expected_version` for a row that must not exist yet, which is how first-write races are
#: detected.
NO_STATE = -1

#: A JSON object. Read as a mapping so that what `load` hands back is not mistaken for something the
#: caller may edit in place and expect stored: a change is a new `save`.
State = Mapping[str, Any]


@dataclass(frozen=True)
class VersionedState:
    """One row: the id it is stored under, the version it is at, and the state itself."""

    id: str
    version: int
    state: State


@dataclass(frozen=True)
class Saved:
    """The save won; the row is now at `version`."""

    version: int


@dataclass(frozen=True)
class VersionConflict:
    """The row was not at the version the caller decided against. `actual_version` is where it is —
    `NO_STATE` when there is no row at all."""

    actual_version: int


SaveResult = Saved | VersionConflict


class Repository(Protocol):
    """Load and save current state by id, with optimistic concurrency on the version."""

    def load(self, id: str) -> VersionedState | None:
        """The row stored under `id`, or `None` when there is none."""
        ...

    def save(self, id: str, expected_version: int, state: State) -> SaveResult:
        """Write `state` if the row is at `expected_version`; report the version it is at if not."""
        ...

    def head(self) -> int:
        """How many rows are stored. The readiness probe asks this, and nothing else does: it is
        the cheapest honest question the store can answer, and a store that cannot answer it is not
        ready."""
        ...


def assert_write(id: str, expected_version: int, state: object) -> None:
    """Refuse a write no adapter could store faithfully, before any adapter is asked to.

    Raised rather than returned, because every case here is a programming error and not contention:
    an empty id, a version that was never read from anywhere, or a value that is not JSON.
    """
    if not isinstance(id, str) or not id.strip():
        raise ValueError("state repository requires an id")
    counted = isinstance(expected_version, int) and not isinstance(expected_version, bool)
    if not counted or expected_version < NO_STATE:
        raise ValueError("expected_version must be NO_STATE or a non-negative integer")
    if not isinstance(state, dict):
        raise ValueError("state repository requires a JSON object")
    _assert_json(state, set())


def _assert_json(value: object, seen: set[int]) -> None:
    """Finite, acyclic, plain JSON: what survives `json.dumps` and back unchanged.

    `json.dumps` alone is not the check. It writes a tuple as a list and an integer key as a string,
    so a value would come back from the store as something other than what was saved, and it accepts
    `NaN` unless asked not to. Each of those is refused here instead.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ValueError("state repository requires finite JSON numbers")
    if not isinstance(value, (dict, list)) or id(value) in seen:
        raise ValueError("state repository requires acyclic JSON objects, arrays and scalars")
    seen.add(id(value))
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("state repository requires JSON objects with string keys")
            _assert_json(item, seen)
    else:
        for item in value:
            _assert_json(item, seen)
    seen.discard(id(value))
