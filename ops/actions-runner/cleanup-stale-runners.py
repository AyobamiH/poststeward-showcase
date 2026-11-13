#!/usr/bin/env python3
"""Compatibility entry point; authoritative implementation is ../cleanup-stale-runners.py.

Do not duplicate GitHub runner deletion logic here. The installed systemd service
uses a copy of the canonical file, not this compatibility entry point.
"""
from pathlib import Path
import runpy

_CANONICAL = Path(__file__).resolve().parent.parent / "cleanup-stale-runners.py"
if __name__ == "__main__":
    runpy.run_path(str(_CANONICAL), run_name="__main__")
else:
    # Preserve legacy test/import call sites without maintaining two algorithms.
    globals().update({
        name: value for name, value in
        runpy.run_path(str(_CANONICAL), run_name="_showcase_canonical_cleanup").items()
        if not name.startswith("__")
    })
