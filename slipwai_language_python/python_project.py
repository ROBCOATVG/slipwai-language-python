"""The Python backend's answers about the project around its services: what git ignores, what an agent may run,
what the gate is called, where the event model's code lives, and what `make mutation` uses.

Moved here from core's per-backend tables (S05), keyed by the protocol's member constants."""
from __future__ import annotations

from ... import registry as protocol
from ...naming import python_package_name


def event_model_paths(project_name: str, service: str) -> dict[str, str]:
    """Where a slice's code lives in a Python service, under the package the project's name becomes."""
    documented_python_package = python_package_name(project_name)
    return {
        "events": f"{service}/src/{documented_python_package}/domain/<context>/events.py",
        "domain": f"{service}/src/{documented_python_package}/domain/<context>/decider.py",
        "usecase": f"{service}/src/{documented_python_package}/application/<context>/<use_case>.py",
        "test": f"{service}/tests/test_<slice>.py (pytest)",
    }


ANSWERS = {
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
