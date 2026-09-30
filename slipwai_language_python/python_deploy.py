"""The Python answers about production and CI: how a service becomes an image, what it is told there, and how
CI sets Python and uv up.

Beside `python.py` rather than inside it so that module keeps room under the line budget for the answers the
other slices move; its `LANGUAGE` merges these in, and they are its answers like any other. The recipe
vocabulary (`__APP__`, `__IMAGE__`, `$(PLATFORM)`) and the pins are core's, in `images.py`.
"""
from __future__ import annotations

from typing import Any

from ... import registry as protocol
from ...backends import APP, PYTHON_VERSION, UV_VERSION
from ...images import CPYTHON_VERSION, PACK
from ...services import App


def ci_toolchain_setup(services: list[App]) -> str:
    """Python from `actions/setup-python`, uv at the factory's pin, and uv's cache keyed on every lock.

    uv is this backend's toolchain, and no runner ships it. Installed from PyPI at the factory's pin rather
    than through a third-party action: this job already asks PyPI for everything else, and an action is one
    more thing that has to resolve on whichever forge the project landed on. The cache is uv's own download
    cache, keyed on the committed locks — `uv sync --locked` installs exactly what they name, so a run that
    changes no lock downloads nothing.
    """
    return (
        "      - uses: actions/setup-python@v6\n        with:\n"
        f"          python-version: '{PYTHON_VERSION}'\n"
        f"      - run: python3 -m pip install --disable-pip-version-check -q uv=={UV_VERSION}\n"
        "      - uses: actions/cache@v4\n        with:\n          path: ~/.cache/uv\n"
        "          key: uv-${{ runner.os }}-${{ hashFiles("
        + ", ".join(f"'{s.path}/uv.lock'" for s in services)
        + ") }}\n"
    )


FAMILY: dict[protocol.Member[Any], object] = {protocol.CI_TOOLCHAIN_SETUP: ci_toolchain_setup}

# `project.toml` beside the service, read by `pack build --path <the service>`: this backend's image builder
# packs that directory alone, so the upload list is written there.
SERVICE_DESCRIPTOR = """# Read by `pack build --path <this directory>` (`make build`): what the upload leaves out.
#
# `uv.lock` is excluded deliberately, and `make build` exports its runtime half to `requirements.txt`
# first. The builder's Python group picks its package manager from what it finds, and a lock in the
# upload sends it to fetch uv from a GitHub release inside the build — a third host to be reachable, for
# a resolution this repository has already done. The exported file carries the same versions and their
# hashes. `.venv` is this machine's environment, for this machine's platform and interpreter; the image
# builds its own.
[_]
schema-version = "0.2"

[io.buildpacks]
exclude = ["uv.lock", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"]
"""

BACKEND: dict[protocol.Member[Any], object] = {
    protocol.IMAGE_BUILDER: {
        "tool": "pack",
        # The service alone: a Python service is self-contained, and the Procfile the target writes beside
        # it is the start command.
        #
        # The requirements file is *exported from the lock* immediately before the build rather than
        # committed, and `--no-dev` is the point of it: the image carries what the service imports when it
        # is running and not the gate's mypy, pytest and ruff. Hashes and all, derived every time, so it
        # can never become a second dependency list that drifts from the first.
        #
        # `uv.lock` itself stays out of the upload (`SERVICE_DESCRIPTOR` above), which is what makes the
        # buildpack read that file: the pinned builder's Python group selects its package manager by what
        # it finds, and a `uv.lock` in the upload sends it to install uv from a GitHub release inside the
        # build. That is a third host to be reachable from wherever `make build` runs, for a resolution
        # this repository has already done and committed. The day the builder ships uv itself, this
        # exclusion and the export both go and the lock is uploaded as it stands.
        "build": (
            f"cd {APP} && uv export --frozen --no-dev --no-emit-project --quiet -o requirements.txt\n\t"
            f"{PACK} --path {APP} --env BP_CPYTHON_VERSION={CPYTHON_VERSION} "
            "--env BP_PIP_REQUIREMENT=requirements.txt $(PACK_FLAGS)"
        ),
    },
    protocol.MIGRATIONS_IN_PRODUCTION: {"command": ["python", "migrations/apply.py"]},
    # psycopg reads it as libpq does, where `require` is "encrypt, do not verify".
    # Per managed-database kind; `images.py`, above `POSTGRES_SSLMODE_KINDS`, says how each was measured.
    protocol.POSTGRES_SSLMODE: {"rds": "require", "flexible-server": "require"},
    protocol.SERVICE_DESCRIPTORS: {"project.toml": SERVICE_DESCRIPTOR},
}
