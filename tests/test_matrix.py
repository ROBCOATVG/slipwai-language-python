"""This package's own generated-variant matrix, against the slipwai it is tested with (FR-036, D100).

Every native-gate variant of each backend this package owns is generated and held to its own `make verify`, and its
production image built and started where Docker is here. That takes minutes and every toolchain, so the case skips
unless `SLIPWAI_MATRIX=1`; `python -m slipwai.matrix <language-dir> python` runs the same cases. The language
directory is the one this package sits in, so the root suite's shims run it against the checkout's pins.
"""
from __future__ import annotations

from pathlib import Path

from slipwai import matrix


class Matrix(matrix.MatrixCase):
    language_dir = Path(__file__).resolve().parents[2]
    package = "python"
