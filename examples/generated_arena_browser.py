"""Launch the generated loopback Arena browser shell.

From the repository root:
  PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py
  ARENA_TRACE_UI=1 PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py
  PYTHONPATH=../npc-generator .venv/bin/python examples/generated_arena_browser.py --port 8001 --authored-draw-scenario
"""
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_browser_session import GeneratedArenaSession
from arena_web import serve_local


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    equipment = parser.add_mutually_exclusive_group()
    equipment.add_argument("--ground-loadout-profile",
                        help="opt in to a caller-authored local JSON ground-equipment profile")
    equipment.add_argument("--authored-draw-scenario", action="store_true",
                        help="opt in to the checked-in ordinary Dagger Draw scenario fixture")
    parser.add_argument("--trace-ui", action="store_true",
                        help="print bounded browser/server/native Arena action traces")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    profile = None
    if args.ground_loadout_profile:
        profile_path = Path(args.ground_loadout_profile).resolve()
        try:
            profile_path.relative_to(ROOT)
        except ValueError:
            parser.error("ground-loadout profile must be inside the repository")
        if not profile_path.is_file():
            parser.error("ground-loadout profile file does not exist")
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            parser.error(f"ground-loadout profile is not readable JSON: {exc}")
    draw_scenario = None
    if args.authored_draw_scenario:
        scenario_path = ROOT / "examples" / "arena_scenarios" / "ordinary-dagger-draw.json"
        try:
            draw_scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            parser.error(f"authored Draw scenario fixture is not readable JSON: {exc}")
    trace_ui = args.trace_ui or os.environ.get("ARENA_TRACE_UI") == "1"
    if trace_ui:
        print("Arena UI terminal tracing enabled.", flush=True)
    serve_local(args.port, session=GeneratedArenaSession(
        trace_ui=trace_ui, ground_loadout_profile=profile,
        authored_draw_scenario=draw_scenario))


if __name__ == "__main__":
    main()
