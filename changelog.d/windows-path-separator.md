PATCH

**A Python service type-checks under Git's bash on Windows.** `scripts/verify` joins `MYPYPATH` with `;`
where `uname -s` names Git's bash, because Python on Windows splits a path list on `;` and MSYS leaves a
relative list as it is; everywhere else it joins with `:`, as before.

**Catch-up.** `slipwai migrate` brings the new `scripts/verify`.
