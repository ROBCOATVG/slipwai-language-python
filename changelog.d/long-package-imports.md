PATCH

**A state-stored Python service with a long package name passes its own lint.** The repository's contract tests
import the adapter in parentheses, so a package name past about twenty characters no longer pushes the line over
100 columns and fails `make verify`.

**Catch-up.** `slipwai migrate` brings the two test files; or wrap the adapter import in
`tests/contract/test_repository_memory.py` and `tests/integration/test_repository_postgres.py` by hand.
