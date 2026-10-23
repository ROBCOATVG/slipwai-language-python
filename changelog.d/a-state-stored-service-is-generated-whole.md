MINOR

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
