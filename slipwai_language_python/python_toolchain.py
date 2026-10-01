"""Python's toolchain: how a service in this language installs, starts, checks and formats itself.

These are the language's answers to the toolchain members of the backend protocol (slipwai's `registry` module,
whose shapes are fixed in its backend-protocol contract). `BACKEND` is
what the `python` backend answers and `FAMILY` what the family does. `python.py`'s `LANGUAGE` takes both in. A
command spells a service's path `APP` and its family's verify script `VERIFY`, which `tooling.for_app` stamps.
"""
from __future__ import annotations

from typing import Any

from slipwai import registry as protocol
from slipwai.backends import APP, PYTHON_VERSION, UV_VERSION, VERIFY, Tooling
from slipwai.naming import python_package_name
from slipwai.tooling import for_app

TOOLING: Tooling = {
    "install": f"./{VERIFY} --install-only",
    "migrate": f"./{VERIFY} --migrate",
    "integration": f"./{VERIFY} --integration-only",
    "ci_image": f"python:{PYTHON_VERSION}-bookworm",
    "ci_install": f"./{VERIFY} --install-only",
    # uv is this backend's toolchain and the official Python images do not ship it, so the two places
    # that run `make` inside one install it first — at the pin in `backends.py`, from PyPI, which is the one
    # registry these jobs already ask anything of.
    "container_setup": f"python3 -m pip install --disable-pip-version-check -q uv=={UV_VERSION}",
    "container_environment": {},
}

# The eight targets every service answers (`native_commands.TARGETS`), in that order. `scripts/verify` loops
# over the services itself, so most of these are one line for the whole project, and `native_commands`
# emits them once.
NATIVE_COMMANDS = {
    "install": f"./{VERIFY} --install-only",
    # Byte-compile, then mypy over the same trees — the shape the factory holds itself to.
    # `compileall` alone is not a type check: it proves the files parse and nothing else.
    "typecheck": f"./{VERIFY} --typecheck-only",
    "lint": f"./{VERIFY} --lint-only",
    "test": f"./{VERIFY} --test-only",
    "integration": f"./{VERIFY} --integration-only",
    "adversarial": f"./{VERIFY} --adversarial-only",
    # Against the lock, exported on the spot — every pin this project resolves to, the gate's
    # tools included, and no committed file for the audit to read a stale copy of.
    "audit": (
        "@command -v pip-audit >/dev/null 2>&1 || { echo 'install pip-audit to run dependency "
        "audit' >&2; exit 2; }; pip-audit -r <(uv export --project "
        f"{APP} --frozen --no-emit-project --no-hashes)"
    ),
    "mutation": "@command -v mutmut >/dev/null 2>&1 || { echo 'install and configure mutmut for the selected production packages' >&2; exit 2; }; mutmut run",
}


def native_commands(path: str, verify: str) -> dict[str, str]:
    """One service's eight commands, spelled for its own directory and its family's verify script."""
    return {target: for_app(command, path, verify) for target, command in NATIVE_COMMANDS.items()}


def dev_command(qualifier: str, path: str, verify: str) -> str:
    """How one service starts in the foreground: installed first, then its package's `main`, pretty-logged."""
    return (
        f"./{verify} --install-only\n\tLOG_FORMAT=pretty PYTHONPATH={path}/src "
        f"uv run --project {path} --no-sync python -m {python_package_name(qualifier)}.main"
    )


def event_store_directory(path: str) -> str:
    """Where one service's driven adapters live, for prose that has to point at them."""
    return f"{path}/src/<package>/adapters/driven/"


BACKEND: dict[protocol.Member[Any], object] = {
    protocol.TOOLING: TOOLING,
    protocol.FEATURE_TOOLING: {},
    protocol.EXECUTABLES: frozenset(),
    protocol.DEV_COMMAND: dev_command,
    # The environment `uv sync` builds beside each service, and uv's own download cache above them.
    protocol.COMPOSE_CACHES: (f"/workspace/{APP}/.venv", "/root/.cache/uv"),
    protocol.EVENT_STORE_DIRECTORY: event_store_directory,
    protocol.NATIVE_COMMANDS: native_commands,
}
FAMILY: dict[protocol.Member[Any], object] = {protocol.FORMATTER: f"./{VERIFY} --format"}
