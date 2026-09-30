"""The Python backend's answers about production: how a service becomes an image, and what it is told there.

Beside `python.py` rather than inside it so that module keeps room under the line budget for the answers the
other slices move; its `LANGUAGE` merges these in, and they are its answers like any other. The recipe
vocabulary (`__APP__`, `__IMAGE__`, `$(PLATFORM)`) and the pins are core's, in `images.py`.
"""
from __future__ import annotations

from typing import Any

from ... import registry as protocol
from ...backends import APP
from ...images import CPYTHON_VERSION, PACK

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
        # `uv.lock` itself stays out of the upload (`images.SERVICE_DESCRIPTORS`, which `descriptor` names),
        # which is what makes the buildpack read that file: the pinned builder's Python group selects its
        # package manager by what
        # it finds, and a `uv.lock` in the upload sends it to install uv from a GitHub release inside the
        # build. That is a third host to be reachable from wherever `make build` runs, for a resolution
        # this repository has already done and committed. The day the builder ships uv itself, this
        # exclusion and the export both go and the lock is uploaded as it stands.
        "build": (
            f"cd {APP} && uv export --frozen --no-dev --no-emit-project --quiet -o requirements.txt\n\t"
            f"{PACK} --path {APP} --env BP_CPYTHON_VERSION={CPYTHON_VERSION} "
            "--env BP_PIP_REQUIREMENT=requirements.txt $(PACK_FLAGS)"
        ),
        "descriptor": "python",
    },
}
