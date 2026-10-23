"""The Python backend's toolchain: a manifest, a committed lock, and uv between them.

Generation alone, no toolchain — whether `uv sync --locked` is *happy* with what the factory ships is
`tests/test_matrix.py`, which runs the real thing. What is here is the shape: that the manifest says what
this project's answers need and nothing else, that a lock resolved from exactly that manifest is committed
beside it, that the gate installs from the lock rather than resolving, and that nothing anywhere still
names `requirements-dev.txt` or the `.python-tools` directory it was installed into.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from slipwai.backends import UV_VERSION
from slipwai.project.pruner import prune_rows
from slipwai.selection import Selection

# This package, imported from the checkout it sits in, beside the directory the keel loads it from.
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))
from slipwai_language_python import python as PYTHON  # noqa: E402

FEATURE_REQUIREMENTS, LOCK_FEATURES = PYTHON.FEATURE_REQUIREMENTS, PYTHON.LOCK_FEATURES
lock_suffix, requirements = PYTHON.lock_suffix, PYTHON.requirements
LOCKS = PACKAGE_ROOT / "assets/languages/python/locks"


class FactoryTestCase(unittest.TestCase):
    """Generation through `slipwai generate`, against whichever language directory the keel was pointed at."""

    def generate(self, parent: str, name: str, profile: str, backend: str, frontend: str, **axes: str) -> Path:
        arguments = [sys.executable, "-m", "slipwai", "generate", name, "--profile", profile, "--backend", backend,
                     "--frontend", frontend, "--output", parent, "--skip-checks", "--no-init"]
        for axis, answer in axes.items():
            arguments += [f"--{axis.replace('_', '-')}", answer]
        subprocess.run(arguments, check=True, capture_output=True)
        return Path(parent) / name


def manifest(repo, service: str = "apps/service") -> dict:
    return tomllib.loads((repo / service / "pyproject.toml").read_text())


class UvTest(FactoryTestCase):
    def test_a_service_carries_its_runtime_dependencies_its_dev_group_and_its_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "uv-full", "event-modelling", "python", "none",
                write_model="events", persistence="postgres", http="fastapi", auth="keycloak",
            )

            document = manifest(repo)
            # What the service imports when it is running — and so what the production image carries.
            self.assertEqual(
                [
                    "fastapi==0.141.1",
                    "opentelemetry-api==1.44.0",
                    "opentelemetry-exporter-otlp-proto-http==1.44.0",
                    "opentelemetry-instrumentation-fastapi==0.65b0",
                    "opentelemetry-sdk==1.44.0",
                    "psycopg[binary]==3.3.4",
                    "pydantic-settings==2.15.0",
                    "uvicorn==0.52.4",
                ],
                document["project"]["dependencies"],
            )
            # And what only the gate needs. `httpx` is here rather than above because it is what
            # `TestClient` drives the app with; a running service never imports it.
            self.assertEqual(
                ["httpx==0.28.1", "mypy==2.3.1", "pytest==9.1.1", "ruff==0.16.3"],
                document["dependency-groups"]["dev"],
            )
            # Not a package: the code reaches the interpreter through PYTHONPATH, so `uv sync` must not
            # try to build a wheel out of `src/`.
            self.assertIs(False, document["tool"]["uv"]["package"])

            lock = (repo / "apps/service/uv.lock").read_text()
            # Renamed with the manifest, because the lock names the project it was resolved for.
            self.assertIn('name = "uv-full-service"', lock)
            self.assertNotIn("delivery-starter", lock)
            for pin in ("fastapi", "psycopg", "uvicorn", "pytest", "ruff", "mypy"):
                self.assertIn(f'name = "{pin}"', lock)
            self.assertFalse((repo / "apps/service/requirements-dev.txt").exists())

    def test_a_bare_service_asks_for_nothing_at_run_time(self) -> None:
        """A walking skeleton imports the standard library and nothing else; the gate's tools still have
        to be there, which is the whole difference between the two lists."""
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(
                directory, "uv-bare", "standard", "python", "none",
                http="none", auth="none",
            )

            document = manifest(repo)
            self.assertEqual([], document["project"]["dependencies"])
            self.assertEqual(
                ["mypy==2.3.1", "pytest==9.1.1", "ruff==0.16.3"], document["dependency-groups"]["dev"]
            )

    def test_the_gate_installs_from_the_lock_and_never_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "uv-gate", "standard", "python", "none")

            verify = (repo / "scripts/verify").read_text()
            # `--locked` and not `--frozen`: the quieter sibling installs a stale lock without a word,
            # which is the failure this gate exists to catch.
            self.assertIn('uv sync --project "$app" --locked --quiet', verify)
            self.assertNotIn("uv sync --project \"$app\" --frozen", verify)
            self.assertIn('run="uv run --project $app --no-sync"', verify)
            # `ruff format` joins `ruff check`, and `--format` is the half that writes.
            self.assertIn('$run ruff format --check "$app/src" "$app/tests"', verify)
            self.assertIn('--format) $run ruff format "$app/src" "$app/tests" ;;', verify)
            # Nothing of the shape this replaced. `pip` survives in exactly one place — the message a
            # machine with no uv gets — and nowhere that runs.
            for gone in (".python-tools", "pip install --target", "requirements-dev.txt"):
                self.assertNotIn(gone, verify)
            self.assertIn(f"python3 -m pip install uv=={UV_VERSION}", verify)

            makefile = (repo / "Makefile").read_text()
            self.assertIn("./scripts/verify --format", makefile)
            self.assertIn(".venv/", (repo / ".gitignore").read_text())
            self.assertNotIn(".python-tools", (repo / ".gitignore").read_text())

    def test_ci_installs_the_pinned_uv_and_caches_on_the_committed_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.generate(directory, "uv-ci", "standard", "python", "none")

            workflow = (repo / ".github/workflows/verify.yml").read_text()
            self.assertIn(f"pip install --disable-pip-version-check -q uv=={UV_VERSION}", workflow)
            self.assertIn("hashFiles('apps/service/uv.lock')", workflow)
            self.assertNotIn("requirements-dev.txt", workflow)


    def test_a_lock_is_committed_for_every_dependency_set_the_axes_can_produce(self) -> None:
        """One per subset of the dependency-adding features, the way the npm locks are — and no more, so a
        feature that stops adding a distribution leaves no orphan behind for `make locks` to keep."""
        wanted = set()
        for chosen in (set(), {"postgres"}, {"fastapi"}, {"fastapi", "postgres"}):
            axes = {}
            if "postgres" in chosen:
                axes["persistence"] = "postgres"
            if "fastapi" in chosen:
                axes["http"] = "fastapi"
            wanted.add(f"uv{lock_suffix(Selection(axes))}.lock")
        self.assertEqual(wanted, {path.name for path in LOCKS.glob("*.lock")})
        self.assertEqual(("fastapi", "postgres"), LOCK_FEATURES)

    def test_what_generation_adds_is_what_the_prune_removes(self) -> None:
        """Two halves of one fact, per feature. A distribution added here and not named there is one a
        pruned project keeps for ever — and unlike npm's, this pair is matched on the name alone, so the
        version may move in a generated project without the prune quietly missing it."""
        base = set(requirements(Selection({}))[0]) | set(requirements(Selection({}))[1])
        for axis, answer, feature in (
            ("persistence", "postgres", "postgres"),
            ("http", "fastapi", "fastapi"),
        ):
            runtime, development = requirements(Selection({axis: answer}))
            added = {pin.split("==")[0] for pin in set(runtime) | set(development) - base}
            added -= {pin.split("==")[0] for pin in base}
            self.assertEqual(
                set(prune_rows(["python"])["python"]["package_edits"][feature]["packages"]), added, feature
            )
            # And the table this reads is the one the manifest is written from.
            self.assertIn(feature, FEATURE_REQUIREMENTS)
