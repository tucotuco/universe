"""Launch the generated loopback Arena browser shell.

From the repository root: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python examples/generated_arena_browser.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import GeneratedArenaSession
from arena_web import serve_local


def main():
    serve_local(8000, session=GeneratedArenaSession())


if __name__ == "__main__":
    main()
