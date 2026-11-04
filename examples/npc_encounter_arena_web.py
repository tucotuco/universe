"""Launch the loopback-only interactive native Encounter Arena.

From the repository root: PYTHONDONTWRITEBYTECODE=1 python examples/npc_encounter_arena_web.py
"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_web import serve_local


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    serve_local(args.port)


if __name__ == "__main__":
    main()
