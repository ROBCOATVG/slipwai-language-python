# slipwai-language-python
slipwai 2.0 language addon: slipwai-language-python

## What this package answers

The `python` backend: a uv-managed service with Ruff, mypy and pytest, FastAPI as its one transport, Keycloak
identity, and every store on both write-model rungs. `language.json` offers `persistence` (`memory`, `sqlite`,
`postgres`), `write-model` (`events`, `state`), `http`, `auth` and `users`.

- **`write-model: events`** keeps the event store: the event port, its memory, SQLite and PostgreSQL adapters, the
  checkpoint store and catch-up runner, the shared contracts, and the event-log migrations.
- **`write-model: state`** keeps current state instead: `application/ports/repository.py` and its memory, SQLite and
  PostgreSQL adapters (`write_side_files`' `state` block, `slipwai_language_python/python_state.py`). A missing
  row is `NO_STATE`; `save` returns a version conflict as a value; PostgreSQL compares and increments the version in
  one statement. `event_model_paths` answers `repository` with the port's path.
- **The seed door.** On the event rung with PostgreSQL, `scripts/seed.py` is the toolchain's `seed` line:
  `make seed-<service> FILE=<json>` appends the events a slice's `try-it.json` gives, idempotently, through the
  event-store port. The prune rows own it with `postgres`.

`python3 -m slipwai.conformance <language-dir> python` is the protocol check. `tests/test_state_skeleton.py` generates
both rungs and checks what each is given; with `SLIPWAI_STATE_NATIVE=1` and a `DATABASE_URL` it also runs every
generated project's `make verify`, the PostgreSQL contracts and a prune from PostgreSQL to memory.
