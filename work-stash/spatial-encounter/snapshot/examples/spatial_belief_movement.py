"""Belief-conditioned movement using observer-owned seeded waypoint knowledge.

Run with ``python examples/spatial_belief_movement.py``. The waypoint is
preloaded into observer two's own BeliefLedger before Encounter progression.
It remains separate from Group-count reports and all authoritative positions.
Encounter movement changes position; RunAction only measures displacement.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'examples'))

from activities import RunAction
from field_observation import BeliefLedger, KnownWaypoint
from spatial import CartesianPosition, ISEAGrid, LocalFrame, LocalPosition
from spatial_belief_inquiry import _decide
from spatial_group_observation import _build_scenario
from spatial_two_observers import _schedule_second_observation


# Initialization input only. Decision-time selection retrieves the value from
# the observer-owned ledger, never from this scenario constant.
INITIAL_WAYPOINT_POSITION = (0.0, -250.0, 1000.0)
INITIAL_LANDMARK_POSITION = (0.0, -250.0, 1000.0)
INITIAL_WAYPOINT_ID = 'observer-two-south-trail-waypoint'
INITIAL_WAYPOINT_SOURCE = 'scenario-map-card:south-trail'


def _prepare_two_boundaries(*, waypoint_position=INITIAL_WAYPOINT_POSITION,
                             grant_waypoint=True, source_id=INITIAL_WAYPOINT_SOURCE,
                             landmark_position=INITIAL_LANDMARK_POSITION,
                             landmark_geometry=None):
    (world, encounter, first_observer, second_observer, group,
     first_ledger, _empty_second_ledger, first_action, first_choice, rng,
     _) = _build_scenario(advance=False)

    # This aligned LocalFrame is explicit scenario context. Entity positions
    # remain authoritative global Cartesian positions in the same basis.
    frame = LocalFrame.aligned_at(CartesianPosition(0, 0, 0))
    encounter.set_local_frame(frame)
    landmark_id = world.make_object('Brick', 'South trail landmark')
    if landmark_id is None:
        raise ValueError('scenario landmark requires the existing Brick Object definition')
    landmark = world.get_object_by_id(landmark_id)
    landmark.set_position(CartesianPosition(*landmark_position))
    if landmark_geometry is not None:
        # The existing geometric path adapter returns "unknown" if any other
        # participating Entity has no modeled shape. This fixture supplies a
        # scenario extent to those candidates; no opacity/perception rule is
        # inferred, and the additional shapes lie away from the Spot segment.
        for entity in (first_observer, second_observer, group, landmark):
            if entity.geometry is None:
                entity.set_geometry(landmark_geometry)
    encounter.add_object(landmark_id)
    if grant_waypoint:
        knowledge = KnownWaypoint(
            INITIAL_WAYPOINT_ID, second_observer.id, source_id, 0.0,
            LocalPosition(*waypoint_position), frame)
        second_ledger = BeliefLedger(second_observer.id,
                                     initial_waypoints=(knowledge,))
    else:
        second_ledger = BeliefLedger(second_observer.id)

    # The grant exists before the first committed boundary and is not derived
    # from either observer's later group observation.
    encounter.step(1)
    second_action, second_choice = _schedule_second_observation(
        world, encounter, second_observer, group, second_ledger)
    encounter.step(1)
    source_provenance = {
        'source_id': source_id if grant_waypoint else None,
        'landmark_id': landmark.id,
        'landmark_name': landmark.name,
        'landmark_local_position_at_initialization': (
            encounter.entity_local_position(landmark.id).as_tuple()),
        'waypoint_claim_local_position': (
            second_ledger.known_waypoints[0].position.as_tuple()
            if grant_waypoint else None),
        'relationship': ('explicit scenario attribution from the map-card source to '
                         'this native Object; not a modeled map or proof the claim is current'),
    }
    return (world, encounter, first_observer, second_observer, group,
            first_ledger, second_ledger, first_action, first_choice, rng,
            second_action, second_choice, frame, landmark, source_provenance)


def _velocity_to_waypoint(encounter, observer, waypoint, duration=1.0):
    """Build a local Encounter velocity from own position and owned knowledge."""
    if duration <= 0:
        raise ValueError('duration must be positive')
    current = encounter.entity_local_position(observer.id).as_tuple()
    destination = waypoint.position.as_tuple()
    return tuple((goal - start) / duration
                 for start, goal in zip(current, destination))


def run_scenario(*, waypoint_position=INITIAL_WAYPOINT_POSITION,
                 grant_waypoint=True, source_id=INITIAL_WAYPOINT_SOURCE,
                 lookup_owner_id=None, lookup_frame=None, advance=True,
                 landmark_position=INITIAL_LANDMARK_POSITION,
                 landmark_geometry=None):
    (world, encounter, first_observer, second_observer, group,
     first_ledger, second_ledger, first_action, first_choice, rng,
     second_action, second_choice, frame, landmark, source_provenance) = _prepare_two_boundaries(
        waypoint_position=waypoint_position, grant_waypoint=grant_waypoint,
        source_id=source_id, landmark_position=landmark_position,
        landmark_geometry=landmark_geometry)

    # The inquiry decision uses only observer two's own committed Group
    # evidence. Its Group-count estimates do not provide the waypoint.
    proposal = _decide(group.id, second_ledger, encounter.time)
    owner = second_observer.id if lookup_owner_id is None else lookup_owner_id
    query_frame = frame if lookup_frame is None else lookup_frame
    try:
        waypoint = second_ledger.known_waypoint(
            INITIAL_WAYPOINT_ID, owner_id=owner, frame=query_frame)
    except (PermissionError, ValueError) as exc:
        waypoint = None
        refusal = str(exc)
    else:
        refusal = None

    if proposal is None or waypoint is None:
        return {
            'world': world, 'encounter': encounter, 'group': group,
            'first_observer': first_observer, 'second_observer': second_observer,
            'first_ledger': first_ledger, 'second_ledger': second_ledger,
            'first_action': first_action, 'second_action': second_action,
            'first_choice': first_choice, 'second_choice': second_choice,
            'landmark': landmark, 'source_provenance': source_provenance,
            'proposal': proposal, 'waypoint': waypoint, 'waypoint_refusal': refusal,
            'run_action': None, 'choice': None,
            'inspection': encounter.inspect_committed(), 'rng': rng, 'frame': frame,
        }

    if (proposal.observer_id != second_observer.id
            or proposal.group_id != group.id
            or proposal.reason != 'uncertain_estimate'):
        raise ValueError('proposal does not authorize this fixture-specific follow-up')

    before_position = second_observer.get_position().as_tuple()
    velocity = _velocity_to_waypoint(encounter, second_observer, waypoint)
    run_action = RunAction(world, second_observer.id, encounter.time, 1,
                           minimum_distance=25, experience=9)
    choice = encounter.schedule_choice((run_action,))
    if advance:
        # This is the native physical movement command; RunAction has no motion
        # behavior. Local velocity uses the same LocalFrame named in knowledge.
        encounter.step(1, velocities={second_observer.id: velocity},
                       velocity_frame='local')
        inspection = encounter.inspect_committed()
        after_position = second_observer.get_position().as_tuple()
        record = inspection.action(run_action.id)
        target = inspection.target(second_observer.id)
        practice = next(batch for batch in target.practice_history
            if any(use.action_id == run_action.id for use in batch.exercises))
    else:
        inspection = encounter.inspect_committed()
        after_position = before_position
        record = practice = None
    grid = ISEAGrid(radius=1.0)
    return {
        'world': world, 'encounter': encounter, 'group': group,
        'first_observer': first_observer, 'second_observer': second_observer,
        'first_ledger': first_ledger, 'second_ledger': second_ledger,
        'first_action': first_action, 'second_action': second_action,
        'first_choice': first_choice, 'second_choice': second_choice,
        'landmark': landmark, 'source_provenance': source_provenance,
        'proposal': proposal, 'waypoint': waypoint, 'waypoint_refusal': None,
        'frame': frame, 'velocity': velocity,
        'before_position': before_position, 'after_position': after_position,
        'run_action': run_action, 'choice': choice, 'inspection': inspection,
        'record': record, 'practice': practice, 'rng': rng,
        'observer_cell': str(second_observer.spatial_cell(grid, 5)),
    }


def demo_data():
    result = run_scenario()
    proposal, action, record = (result['proposal'], result['run_action'],
                                result['record'])
    waypoint = result['waypoint']
    practice = result['practice']
    displacement = dict(record.facts.metadata)['displacement']
    return {
        'coordinate_contract': 'scenario-local Cartesian frame; no planetary or geographic datum',
        'decision': {
            'policy': 'native InquiryPolicy(relative_uncertainty_threshold=0.5)',
            'scope': 'fixture-specific: a qualifying dogs inquiry proposal selects this known-waypoint run',
            'observer_id': proposal.observer_id,
            'reason': proposal.reason,
            'category': proposal.category,
            'time': proposal.time,
            'source_evidence_ids': proposal.evidence_ids,
        },
        'destination_knowledge': {
            'id': waypoint.id,
            'owner_id': waypoint.owner_id,
            'source_id': waypoint.source_id,
            'acquired_at': waypoint.acquired_at,
            'local_position': waypoint.position.as_tuple(),
            'local_frame': waypoint.frame.to_dict(),
        },
        'objective_landmark': {
            'id': result['landmark'].id,
            'name': result['landmark'].name,
            'actual_global_position': result['landmark'].get_position().as_tuple(),
            'actual_local_position': result['encounter'].entity_local_position(
                result['landmark'].id).as_tuple(),
        },
        'detached_source_provenance': result['source_provenance'],
        'movement_command': {
            'api': 'Encounter.step(duration=1, velocities=..., velocity_frame="local")',
            'velocity_local': result['velocity'],
            'start_position_global': result['before_position'],
            'end_position_global': result['after_position'],
        },
        'run_action': {
            'action_id': action.id,
            'choice_id': result['choice'].id,
            'boundary': record.resolved_boundary,
            'outcome': record.facts.outcome,
            'measured_displacement': displacement,
            'target_ids': record.facts.target_ids,
        },
        'target_owned_practice': {
            'target_id': result['second_observer'].id,
            'experience': practice.experience,
            'time': practice.time,
            'causal_action_ids': tuple(row.action_id for row in practice.exercises),
        },
        'observer_one_has_no_waypoint': not result['first_ledger'].known_waypoints,
        'group_unchanged': {
            'position': result['group'].get_position().as_tuple(),
            'materialized_beings': result['group'].materialized_count,
        },
        'derived_isea_cell': result['observer_cell'],
        'committed_boundaries': tuple(row.boundary for row in
            result['encounter'].__dict__['_atomic_interval_history']),
    }


if __name__ == '__main__':
    print(json.dumps(demo_data(), indent=2, sort_keys=True))
