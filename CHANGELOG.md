# Changelog

No releases yet. Release notes are recorded here newest first, one entry per released version; the entry being
written is `changelog.d/`.

## 1.0.0

**Python is now a language package of its own.** The Python backend that was built into slipwai — its service
skeleton on uv, Ruff and pytest, its event-store adapters, its FastAPI transport, identity wiring, mutation gate,
committed uv locks and the Procfile its buildpack image starts from — lives here, with the history it had there,
and slipwai loads it from its language directory (`$SLIPWAI_LANGUAGES`, or `~/.slipwai/languages`). The projects
it generates are byte for byte those slipwai generated with Python built in. It carries its own copy of the
event-log schema (`assets/backing-services/sql/`), and it declares the catalog schema it loads on,
`core >=9.0,<10`, in `language.json`.

