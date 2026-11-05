"""Two-process, host-approved read-only inspection of the Arena history.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 python examples/arena_history_admission.py

The child accepts one exact locally selected prefix. It does not restore or
resume an Encounter and does not install publisher receipts.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from arena_history_prefix import capture_arena_history_prefix
from npc_encounter_arena import build_arena


_CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from arena_history_prefix import decode_arena_history_prefix
from arena_history_admission import (
    ExpectedArenaBinding,
    ExpectedArenaScenario,
    _host_authorize_arena_history,
    _prepare_arena_history_view,
)
assert 'atomic_publication' not in sys.modules
assert 'encounter' not in sys.modules
assert 'checkpoint_restore_preparation' not in sys.modules
prefix = decode_arena_history_prefix(sys.stdin.buffer.read())
expected = (
    ExpectedArenaBinding(
        'arena-ari',
        'fbbee87dab9b7047b13ee11bb4ad37385779381f60d1dfc3c230afc5251befde',
        'Ari', 'arena/being/ari', 'Human',
        ('0x0.0p+0', '0x0.0p+0', '0x0.0p+0')),
    ExpectedArenaBinding(
        'arena-bex',
        '9da574a288bd4f62832324e30c38426c9e666988628e2989c713db28c8007570',
        'Bex', 'arena/being/bex', 'Human',
        ('0x1.8000000000000p+1', '0x0.0p+0', '0x0.0p+0')),
)
scenario = ExpectedArenaScenario(
    '0', 'npc-arena/encounter/1', 'npc-arena/action/spot-ari-bex',
    'arena/being/ari', 'arena/being/bex', '0x0.0p+0', 6)
# This explicit host call is the local policy decision; the digest by itself
# only checks exact content and never creates an admission capability.
capability = _host_authorize_arena_history(
    prefix, expected_content_sha256=prefix.content_sha256,
    expected_scenario=scenario, expected_bindings=expected)
view = _prepare_arena_history_view(prefix, capability)
assert 'atomic_publication' not in sys.modules
assert 'encounter' not in sys.modules
assert view.observer_view('arena/being/ari').aware_of == ('arena/being/bex',)
assert view.observer_view('arena/being/bex').aware_of == ()
print(json.dumps(view.host_summary(), sort_keys=True, separators=(',', ':')))
'''


def main():
    source = build_arena(die_roll=20)
    prefix = capture_arena_history_prefix(source)
    process_b = subprocess.run(
        [sys.executable, "-c", _CHILD, str(ROOT / "src")],
        input=prefix.to_bytes(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=ROOT, check=False)
    if process_b.returncode:
        raise RuntimeError(process_b.stderr.decode("utf-8", errors="replace"))
    output = json.loads(process_b.stdout)
    print("Process A exported the native six-boundary Arena prefix.")
    print("Process B explicitly host-approved and prepared a detached inspection view.")
    print("NOT a live restored Encounter; no authoritative continuation.")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
