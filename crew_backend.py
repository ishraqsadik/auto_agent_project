"""Shim for legacy imports: `from crew_backend import run_crew_backend`."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from auto_agent.agents.crew_backend import run_crew_backend  # noqa: E402, F401
