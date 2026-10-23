#!/usr/bin/env python3
"""The seed door: append the events a slice's `try-it.json` *gives*, through the store port.

    make seed-<service> FILE=<json>

The file is a list of `{"stream", "event", "data"}`: the events a story needs that the slice
which would have written them has not been built yet — a view seeded to a state, so a person can
judge it before its producers exist. They go in the way every event goes in: through this
service's event-store port, at the stream's current version, each attributed to a system actor
and to one correlation id for the run. Never through an HTTP route — this is a process with the
store's credentials, and the app serves no door.

**A replay records nothing twice.** An event's identity here is the hash of its stream, its type
and its data; one already on the stream with the same hash is skipped, so seeding the same
stories into the same database again adds nothing. **It needs the durable store**: with no
`DATABASE_URL` there is no log to append to, and this says so and exits 2, rather than seeding
an in-memory store the next process would never see.

A plain script beside the service rather than a module inside its package, for the reason
`migrations/apply.py` is: application code must never be able to import the door.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Who the log says wrote a seeded event: no person did, and the log should not pretend one had.
SEED_ACTOR_KIND, SEED_ACTOR_ID = "system", "seed-door"

NO_DATABASE = (
    "seed: DATABASE_URL is unset, so there is no durable store to append to. The seed door "
    "needs the database `make services-up` starts; an in-memory store would be gone before "
    "the app read it."
)


def identity(stream: str, event_type: str, data: Mapping[str, object]) -> str:
    """The same event given twice has the same identity, whatever order its keys are in."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{stream}\0{event_type}\0{canonical}".encode()).hexdigest()


def read_given(path: str) -> list[dict[str, Any]]:
    """The file's events, each checked for the three fields the door needs, before any write."""
    parsed = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(parsed, list):
        raise ValueError(f"{path} is a list of {{stream, event, data}}")
    given = []
    for number, one in enumerate(parsed, start=1):
        if not isinstance(one, dict):
            raise ValueError(f"given {number} is not an object")
        if not isinstance(one.get("stream"), str) or not one["stream"].strip():
            raise ValueError(f"given {number} names no stream")
        if not isinstance(one.get("event"), str) or not one["event"].strip():
            raise ValueError(f"given {number} names no event")
        if not isinstance(one.get("data"), dict):
            raise ValueError(f"given {number}'s data is an object in the model's shape")
        given.append(one)
    return given


def main(arguments: list[str]) -> int:
    if not arguments:
        print(
            "seed: give the file of events to append — make seed-<service> FILE=<json>",
            file=sys.stderr,
        )
        return 1
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print(NO_DATABASE, file=sys.stderr)
        return 2
    given = read_given(arguments[0])

    # Imported after the checks above, so a missing file or an unset URL is reported without the
    # driver — and the package is importable only from the environment the gate built.
    import psycopg

    from delivery_starter.adapters.driven.event_store_postgres import create_postgres_event_store
    from delivery_starter.application.ports.events import (
        Actor,
        Appended,
        DomainEvent,
        create_correlation_id,
        current_version,
    )

    correlation = create_correlation_id(uuid.uuid4())
    appended = skipped = 0
    with psycopg.connect(url) as connection:
        store = create_postgres_event_store(connection)
        for one in given:
            existing = store.read(one["stream"])
            seen = {identity(event.stream_id, event.type, event.payload) for event in existing}
            if identity(one["stream"], one["event"], one["data"]) in seen:
                skipped += 1
                continue
            event = DomainEvent(
                type=one["event"],
                schema_version=1,
                stream_id=one["stream"],
                payload=one["data"],
                occurred_at=datetime.now(UTC).isoformat(),
                actor=Actor(kind=SEED_ACTOR_KIND, id=SEED_ACTOR_ID),
                correlation_id=correlation,
            )
            result = store.append(one["stream"], current_version(existing), [event])
            if not isinstance(result, Appended):
                print(
                    f"seed: {one['event']} on {one['stream']} was not appended: the stream "
                    f"moved to version {result.actual_version} while this ran. Run it again.",
                    file=sys.stderr,
                )
                return 1
            appended += 1
    print(f"seed: {appended} event(s) appended, {skipped} already there")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (OSError, ValueError) as failure:
        print(f"seed: {failure}", file=sys.stderr)
        sys.exit(1)
