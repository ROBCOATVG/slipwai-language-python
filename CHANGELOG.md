# Changelog

No releases yet. Release notes are recorded here newest first, one entry per released version; the entry being
written is `changelog.d/`.

## 1.1.2 — PATCH

**A state-stored Python service with a long package name passes its own lint.** The repository's contract tests
import the adapter in parentheses, so a package name past about twenty characters no longer pushes the line over
100 columns and fails `make verify`.

**Catch-up.** `slipwai migrate` brings the two test files; or wrap the adapter import in
`tests/contract/test_repository_memory.py` and `tests/integration/test_repository_postgres.py` by hand.

## 1.1.1 — PATCH

**A Python service type-checks under Git's bash on Windows.** `scripts/verify` joins `MYPYPATH` with `;`
where `uname -s` names Git's bash, because Python on Windows splits a path list on `;` and MSYS leaves a
relative list as it is; everywhere else it joins with `:`, as before.

**Catch-up.** `slipwai migrate` brings the new `scripts/verify`.

## 1.1.0 — MINOR

**A state-stored Python service is generated whole.** A service on the `state` rung (`write-model: state`) used to
be given none of the store's files — `write_side_files` declared the event-sourced rung only — while its entry point
was still wired to open an event store it did not have, so it could not import itself. The state rung now has its
own rows: a versioned repository port (`application/ports/repository.py`: `NO_STATE`, `load`, `save` returning
`Saved` or `VersionConflict` as a value, `head` for `/ready`) with memory, SQLite and PostgreSQL adapters, one
optimistic-concurrency contract all three pass (Postgres proves it against independent connections, exactly one
winner of the first insert and of an update), the `001_states.sql` migration, and the FastAPI transport and identity
wiring the event rung already had. The entry point opens the repository through the same marked region the event
store's opener uses, so `scripts/backing-services.py --persistence memory` prunes it the same way. Non-JSON state —
`NaN`, a `datetime`, a tuple, a non-string key — is refused before anything is written. `event_model_paths` answers
`repository`, the toolchain answers `persistence_directory` (the member `event_store_directory` was renamed to), and
`language.json` offers the `persistence` and `write-model` axes by the names the core asks them.

**Catch-up:** a state-stored Python project generated with 1.0.0 is missing its service files, and `slipwai replay`
keeps only the features whose files are on disk — so put one PostgreSQL file in place first
(`apps/<service>/migrations/001_states.sql` from this package's `assets/backing-services/sql/`), replay, remove it,
then merge the replay. An event-sourced project needs nothing: its files are unchanged but for one comment in
`main.py` naming `--persistence` where it said `--event-store`, and an integration test that asserted a tag read
returns a list where the port has always returned a tuple. Requires a core with the service write-model protocol
(slipwai 2.x from the per-service rung onward).

**A slice's story may be given its inputs, through the service's own seed door.** A service on the durable store
gains `scripts/seed.py`, run by `make seed-<service> FILE=<json>`: it appends the events a slice's `try-it.json`
*gives* — the ones an unbuilt upstream slice would have written — through the event-store port, at the stream's
current version, as a system actor, with an identity hashed from stream, type and data so a replay records nothing
twice. With no `DATABASE_URL` it says so and exits 2. Never an HTTP route: the door is a process with the store's
credentials. slipwai's Try it runs it before a story's first step, and the Demo rung's seed check runs it in the
berth.

**Catch-up:** `slipwai language upgrade python`, then `slipwai migrate`; the service gains the script and the
Makefile target. Until then a story's `given` is validated by `check-try` and not applied, and Try it says *no seed
door yet*.

## 1.0.0

**Python is now a language package of its own.** The Python backend that was built into slipwai — its service
skeleton on uv, Ruff and pytest, its event-store adapters, its FastAPI transport, identity wiring, mutation gate,
committed uv locks and the Procfile its buildpack image starts from — lives here, with the history it had there,
and slipwai loads it from its language directory (`$SLIPWAI_LANGUAGES`, or `~/.slipwai/languages`). The projects
it generates are byte for byte those slipwai generated with Python built in. It carries its own copy of the
event-log schema (`assets/backing-services/sql/`), and it declares the catalog schema it loads on,
`core >=9.0,<10`, in `language.json`.

