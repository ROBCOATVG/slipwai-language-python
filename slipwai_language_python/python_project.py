"""The Python backend's answers about the project around its services: what git ignores, what an agent may run,
what the gate is called, where the event model's code lives, and what `make mutation` uses.

Moved here from core's per-backend tables (S05), keyed by the protocol's member constants."""
from __future__ import annotations

from typing import Any

from slipwai import registry as protocol
from slipwai.backends import PYTHON_VERSION
from slipwai.naming import python_package_name
from slipwai.project.renovate import WORKFLOWS, RenovateRules
from slipwai.services import App
from slipwai.tooling import service_qualifier


def event_model_paths(project_name: str, service: str) -> dict[str, str]:
    """Where a slice's code lives in a Python service, under the package the project's name becomes."""
    documented_python_package = python_package_name(project_name)
    return {
        "events": f"{service}/src/{documented_python_package}/domain/<context>/events.py",
        "domain": f"{service}/src/{documented_python_package}/domain/<context>/decider.py",
        "usecase": f"{service}/src/{documented_python_package}/application/<context>/<use_case>.py",
        "test": f"{service}/tests/test_<slice>.py (pytest)",
    }


def procfile(project_name: str, service: App) -> str:
    """The start command of a Python service, for the buildpack: it has no other way to know that the package
    lives under `src/`. Nothing else in the project reads this file."""
    package = python_package_name(service_qualifier(project_name, service))
    return (
        "# The production start command, read by the Paketo buildpack `make build` runs; `make dev` does\n"
        "# not use it. `src` is prepended to PYTHONPATH because the package lives under src/, exactly as\n"
        "# scripts/verify says — prepended, not set, because the buildpack's own PYTHONPATH is where the\n"
        "# installed packages are; replacing it starts a container that cannot import uvicorn.\n"
        f"web: PYTHONPATH=src:$PYTHONPATH python -m {package}.main\n"
    )


# One CPython minor for the project, at its root, derived from the constant CI and the image read (`pins.py`).
# Renovate reads `pyproject.toml` and the `uv.lock` beside it through `pep621`, `.python-version` through `pyenv`,
# and the CPython minor CI installs through a custom manager, because no manager reads an action's inputs.
RENOVATE = RenovateRules(
    managers=("pep621", "pyenv"),
    group=("python", ("pep621",), "the Python services' dependencies, and the uv lock beside each manifest"),
    toolchain={
        "customType": "regex",
        "description": "The CPython minor `actions/setup-python` installs, which no manager reads.",
        "managerFilePatterns": [WORKFLOWS],
        "matchStrings": ["python-version: '?(?<currentValue>\\d+\\.\\d+(?:\\.\\d+)?)'?"],
        "depNameTemplate": "python",
        "datasourceTemplate": "python-version",
    },
)
FAMILY_ANSWERS: dict[protocol.Member[Any], object] = {
    protocol.PIN_FILES: {".python-version": f"{PYTHON_VERSION}\n"},
    protocol.MAKEFILE_VARIABLES: None,
    protocol.RENOVATE_RULES: RENOVATE,
}
ANSWERS: dict[protocol.Member[Any], object] = {
    protocol.PROCFILE: procfile,
    protocol.OPT_IN_FLAG_TRANSPORTS: frozenset(),
    # `.venv/` is what `uv sync` builds beside each service's manifest, from the committed `uv.lock`
    # that *is* committed. `apps/*/requirements.txt` is the runtime half of that lock, exported by
    # `make build` for the buildpack and thrown away after: derived from the lock, never edited, and a
    # committed copy would be the second dependency list this backend exists without.
    protocol.GITIGNORE: "__pycache__/\n*.pyc\n.venv/\n.pytest_cache/\n.ruff_cache/\n/apps/*/requirements.txt\n",
    protocol.AGENT_PERMISSIONS: ["python3 *", "python -m pytest *", "python -m ruff *"],
    protocol.GATE_DESCRIPTION: "Ruff and pytest",
    protocol.EVENT_MODEL_PATHS: event_model_paths,
    protocol.MUTATION_TOOL: "mutmut",
}
