"""Historical Group composition queries versus retrospective realization.

Run from root: python examples/historical_group_realization.py
"""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from statistical_group import StatisticalGroup


def run_experiment():
    cfg = json.loads((ROOT / 'examples/nomadic_group.json').read_text())
    group = StatisticalGroup(cfg['group_name'], cfg['group_id'], cfg, cfg['seed'])
    unresolved = group.state_at(0)
    group.advance(100)
    root = group.refine_formation_at(40)
    one_household = group.refine_formation_at(60, household=0)
    partial = group.state_at(0)
    # Requesting the original composition at time 100 need not materialize
    # any member, though it commits the remaining statistical counts.
    fully_committed = group.counts()
    historical = group.state_at(0)
    future = group.state_at(100)
    return locals()


if __name__ == '__main__':
    result = run_experiment()
    print('Before inquiry:', result['unresolved']['formation_composition'])
    print('Committed number of households:', result['root'])
    print('First household:', result['one_household'])
    print('Still unresolved households:', result['partial']['households_unresolved'])
    print('Composition at time 0:', result['historical']['current_composition'])
    print('Composition at time 100:', result['future']['current_composition'])
    print('Realized individual Beings:', result['group'].realized_being_count)
