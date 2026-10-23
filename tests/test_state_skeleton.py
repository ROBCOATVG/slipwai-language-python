"""Generate through the keel, then hold both write-model rungs to what each is given.

Generation is fast and needs no toolchain, so the shape is checked on every run: a service answered
`write-model: state` gets the repository port and its adapters and no log, one answered `events` keeps the log,
and the durable store brings the seed door on the event-sourced rung. The native gates — `make verify` on every
adapter of both rungs, the Postgres contracts, and a prune from Postgres back to memory — opt in with
`SLIPWAI_STATE_NATIVE=1` and a `DATABASE_URL`, because they need uv and a database.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from slipwai.matrix.rows import Row
from slipwai.matrix.run import generate

PACKAGE_PARENT = Path(__file__).resolve().parents[2]


class StateSkeletonTest(unittest.TestCase):
    def generated(self, rung: str, persistence: str, profile: str = "event-modelling", http: str = "fastapi") -> Path:
        parent = Path(tempfile.mkdtemp(prefix="slipwai-py-state-"))
        self.addCleanup(shutil.rmtree, parent, True)
        answers: tuple[tuple[str, str], ...] = (("target", "none"),)
        if profile == "event-modelling":
            answers += (("write-model", rung), ("persistence", persistence), ("http", http),
                        ("auth", "none"), ("users", "none"))
        name = f"proof-{rung}-{persistence}"
        repo, said = generate(PACKAGE_PARENT, parent, Row(name, profile, "python", "none", answers))
        self.assertIsNotNone(repo, said)
        assert repo is not None
        return repo

    @staticmethod
    def package(repo: Path) -> Path:
        return next((repo / "apps/service/src").iterdir())

    def test_state_selects_the_repository_and_no_event_history_for_every_adapter(self) -> None:
        for persistence in ("memory", "sqlite", "postgres"):
            with self.subTest(persistence=persistence):
                repo = self.generated("state", persistence)
                service, package = repo / "apps/service", self.package(repo)
                self.assertTrue((package / "application/ports/repository.py").is_file())
                self.assertTrue((service / "tests/contract/test_repository_memory.py").is_file())
                self.assertFalse((package / "application/ports/events.py").exists())
                self.assertFalse((package / "projections.py").exists())
                main = (package / "main.py").read_text(encoding="utf-8")
                self.assertIn("def open_repository(settings: Settings)", main)
                # The SQLite file's path keeps its setting's name; nothing opens or imports an event store.
                for gone in ("open_event_store", "event_store_memory", "event_store_sqlite", "event_store_postgres"):
                    self.assertNotIn(gone, main)
                self.assertNotIn("__STORE", main)
                if persistence != "memory":
                    self.assertIn(f"# backing-service:{persistence}:begin", main)
                if persistence == "postgres":
                    self.assertTrue((service / "migrations/001_states.sql").is_file())
                    self.assertFalse((service / "migrations/001_events.sql").exists())
                    self.assertFalse((service / "scripts/seed.py").exists())

    def test_events_keep_the_log_and_the_durable_store_brings_the_seed_door(self) -> None:
        repo = self.generated("events", "postgres")
        service, package = repo / "apps/service", self.package(repo)
        self.assertTrue((package / "application/ports/events.py").is_file())
        self.assertFalse((package / "application/ports/repository.py").exists())
        self.assertTrue((service / "migrations/001_events.sql").is_file())
        seed = (service / "scripts/seed.py").read_text(encoding="utf-8")
        # Renamed with the package, as every module under `src/` and `tests/` is.
        self.assertIn(f"from {package.name}.adapters.driven.event_store_postgres import", seed)
        self.assertNotIn("delivery_starter", seed)
        makefile = (repo / "Makefile").read_text(encoding="utf-8")
        self.assertIn("seed-service:", makefile)
        self.assertIn("apps/service/scripts/seed.py $(FILE)", makefile)
        bare = self.generated("events", "memory")
        self.assertFalse((bare / "apps/service/scripts/seed.py").exists())
        self.assertNotIn("seed-service:", (bare / "Makefile").read_text(encoding="utf-8"))

    @unittest.skipUnless(os.environ.get("SLIPWAI_STATE_NATIVE") == "1", "native rung proof is opt-in")
    def test_both_rungs_pass_their_real_gates_and_the_postgres_contracts(self) -> None:
        url = os.environ.get("DATABASE_URL", "")
        self.assertTrue(url, "DATABASE_URL is required for the PostgreSQL contracts")
        self.assertIsNotNone(shutil.which("uv"), "install uv before the native proof")
        for rung in ("state", "events"):
            for persistence in ("memory", "sqlite", "postgres"):
                with self.subTest(rung=rung, persistence=persistence):
                    repo = self.generated(rung, persistence)
                    self.run_gate(["make", "verify"], repo)
                    if persistence != "postgres":
                        continue
                    self.run_gate(["make", "migrate", "test-integration", f"DATABASE_URL={url}"], repo)
                    if rung == "state":
                        self.run_gate(["python3", "scripts/backing-services.py", "--persistence", "memory"], repo)
                        self.assertFalse(next(repo.glob("apps/service/src/*/adapters/driven/repository_postgres.py"), None))
                        self.run_gate(["make", "verify"], repo)

    def run_gate(self, command: list[str], repo: Path) -> None:
        done = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=600)
        self.assertEqual(done.returncode, 0, done.stdout[-12000:] + done.stderr[-6000:])
