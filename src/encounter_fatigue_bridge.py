"""Minimal native freeze-only Q/B boundary for Encounter Patch 1.

The independent integration bridge discussed in the Universe 4 handoff was
not delivered. This supplies ONLY immutable common snapshots and the adopted
check modifier. Work consolidation, R4 settlement, action modifier wiring and
transactional commits are deliberately deferred, rather than guessed.
"""
from dataclasses import dataclass
from types import MappingProxyType

from standard_fatigue_check import physical_check_penalty
from physical_fatigue import PhysicalFatigueState
from physical_work import WorkTimeline
from universe_physical_fatigue_r4 import State, evolve


@dataclass(frozen=True)
class FrozenFatigueView:
    being_id: str
    q: float
    b: float
    physiology_id: str | None
    check_modifier: int

    def to_dict(self):
        return {'q': self.q, 'b': self.b,
                'physiology_id': self.physiology_id,
                'check_modifier': self.check_modifier}


class FrozenFatigueFrame:
    """Read-only per-Being Q/B and check views captured at one simulation instant."""

    def __init__(self, beings, registry=None):
        views = {}
        profiles = {}
        for being in beings:
            state = being.get_physical_fatigue()
            if being.id in views:
                raise ValueError('duplicate Being in frozen fatigue frame')
            if registry is not None:
                profiles[being.id] = MappingProxyType({
                    mode: registry.resolve(being, mode=mode)
                    for mode in ('ordinary', 'running')})
            views[being.id] = FrozenFatigueView(
                being.id, state.q, state.b, being.physiology_id,
                -physical_check_penalty(state.q, state.b))
        self._views = MappingProxyType(dict(sorted(views.items())))
        self._profiles = MappingProxyType(dict(sorted(profiles.items())))

    def view(self, being_id):
        return self._views[being_id]

    def to_dict(self):
        return {being_id: view.to_dict() for being_id, view in self._views.items()}

    def physiology(self, being_id, *, mode='ordinary'):
        """Resolve the version-frozen physiology used at this frame."""
        if being_id not in self._profiles:
            raise RuntimeError('no physiology registry was supplied when the frame was frozen')
        return self._profiles[being_id][mode]

    def propose_work(self, timeline, *, max_step=0.25):
        """Run unchanged R4 on a strictly consolidated, complete work timeline.

        This does not mutate native Beings or World state. Failures are atomic:
        no proposals are returned if any participant is infeasible. Only the
        owning native transaction may eventually apply compatible proposals.
        """
        if not isinstance(timeline, WorkTimeline):
            raise TypeError('expected a validated WorkTimeline')
        if set(self._views) != timeline.participant_ids:
            raise ValueError('timeline must cover exactly the frozen Encounter Beings')
        if set(self._views) != set(self._profiles):
            raise RuntimeError('cannot propose R4 depletion without frozen physiology')
        if isinstance(max_step, bool) or not isinstance(max_step, (int, float)) or not 0 < max_step <= 2:
            raise ValueError('max_step must be in (0, 2] seconds')
        proposals = {}
        for being_id in self._views:
            view = self._views[being_id]
            state = State(view.q, view.b)
            versions = []
            was_capped = False
            for segment in timeline.segments(being_id):
                resolved = self.physiology(being_id, mode=segment.physiology_mode)
                versions.append(resolved.version_hash)
                result = evolve(state, segment.requested_u,
                    segment.end - segment.start, resolved.profile,
                    wear=segment.wear, sleep=segment.mode == 'sleep',
                    max_step=max_step)
                if result.capped and segment.mode != 'all_out':
                    raise InsufficientOutput(
                        f'Being {being_id}: {segment.mode} work from '
                        f'{segment.start} to {segment.end} is infeasible; '
                        'record the actual attempted work instead')
                was_capped |= result.capped
                state = result.state
            proposals[being_id] = FatigueProposal(
                being_id, PhysicalFatigueState(view.q, view.b),
                PhysicalFatigueState(state.q, state.b), tuple(versions), was_capped)
        return MappingProxyType(proposals)


@dataclass(frozen=True)
class FatigueProposal:
    """A write-free proposal awaiting the native Being/Object transaction."""
    being_id: str
    before: object  # PhysicalFatigueState, immutable
    after: object
    profile_versions: tuple
    capped: bool

    def to_dict(self):
        return {'being_id': self.being_id,
                'before': {'q': self.before.q, 'b': self.before.b},
                'after': {'q': self.after.q, 'b': self.after.b},
                'profile_versions': list(self.profile_versions),
                'capped': self.capped}


class InsufficientOutput(ValueError):
    """The required/realized workload cannot be maintained for its interval."""
