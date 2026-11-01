"""Current Group-observation exploration slice: deliberate Spot, exact count.

The earlier uncertainty-conditioned follow-up branch depended on provisional
noisy Group sampling and is no longer an honest example under the interim
perfect-observation decision. Run this focused replacement with
``python examples/spatial_exploration_sequence.py``. Run/movement primitives
remain covered by their independent examples and tests.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples'))

from spatial_exact_group_spot import demo_data, run_scenario


if __name__ == '__main__':
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
