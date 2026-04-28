"""Shim for legacy imports: `from tools import log_agent_action`."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from auto_agent.agents.tools import (  # noqa: E402, F401
    book_appointment,
    get_repair_estimate,
    log_agent_action,
)
