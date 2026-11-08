"""Launch the generated loopback Arena browser shell.

From the repository root:
  PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py
  ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py
"""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import GeneratedArenaSession
from arena_web import serve_local


def main():
    trace_ui = os.environ.get("ARENA_TRACE_UI") == "1"
    if trace_ui:
        print("Arena UI terminal tracing enabled (ARENA_TRACE_UI=1).", flush=True)
    serve_local(8000, session=GeneratedArenaSession(trace_ui=trace_ui))


if __name__ == "__main__":
    main()
