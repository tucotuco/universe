"""Launch the loopback-only interactive native Encounter Arena.

From the repository root: PYTHONDONTWRITEBYTECODE=1 python examples/npc_encounter_arena_web.py
"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from arena_web import ArenaSession, serve_local
from arena_local_checkpoint import (ArenaLocalCheckpointRejected,
    activate_approved_local_bundle, activate_approved_s7_bundle,
    read_local_bundle, validate_local_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--save-path", help="host-configured absolute bundle destination outside the repository")
    parser.add_argument("--resume-from", help="host-selected saved bundle; requires --approve-local-checkpoint")
    parser.add_argument("--approve-local-checkpoint", action="store_true",
                        help="explicitly trust the exact fixed local Arena bundle for this process")
    parser.add_argument("--approve-local-s7-checkpoint", action="store_true",
                        help="separately approve the exact post-boundary-7 S7 claim for one boundary-8 Run")
    parser.add_argument("--rng-seed", type=int,
                        help="new host-selected process-local RNG seed; required with --resume-from")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    if args.resume_from:
        if args.rng_seed is None:
            parser.error("--resume-from requires a separately host-selected --rng-seed")
        try:
            wire = read_local_bundle(args.resume_from, repository_root=ROOT)
            import json
            schema = json.loads(wire.decode("utf-8")).get("schema")
            if schema == "universe.arena.local-s7-claim/1":
                if not args.approve_local_s7_checkpoint or args.approve_local_checkpoint:
                    parser.error("S7 requires its separate --approve-local-s7-checkpoint approval")
                active = activate_approved_s7_bundle(
                    args.resume_from, repository_root=ROOT,
                    fixture_root=ROOT / "examples" / "npc_candidates",
                    host_approved=True, rng_seed=args.rng_seed)
            else:
                if args.approve_local_s7_checkpoint:
                    parser.error("S6 requires --approve-local-checkpoint, not the S7 approval flag")
                if not args.approve_local_checkpoint:
                    parser.error("--resume-from requires the separate --approve-local-checkpoint option")
                active = activate_approved_local_bundle(
                    args.resume_from, repository_root=ROOT,
                    fixture_root=ROOT / "examples" / "npc_candidates",
                    host_approved=True, rng_seed=args.rng_seed)
            if args.save_path:
                args.save_path = str(validate_local_path(args.save_path, repository_root=ROOT))
            session = ArenaSession(active=active, save_path=args.save_path)
        except (ArenaLocalCheckpointRejected, OSError, ValueError) as exc:
            parser.error(f"saved Arena was refused: {exc}")
    else:
        if args.approve_local_checkpoint or args.approve_local_s7_checkpoint or args.rng_seed is not None:
            parser.error("approval and RNG options are valid only with --resume-from")
        if args.save_path:
            try:
                args.save_path = str(validate_local_path(args.save_path, repository_root=ROOT))
            except ArenaLocalCheckpointRejected as exc:
                parser.error(f"save destination is invalid: {exc}")
        session = ArenaSession(save_path=args.save_path)
    serve_local(args.port, session=session)


if __name__ == "__main__":
    main()
