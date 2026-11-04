"""Owner-scoped historical location evidence acquired by native Spot.

This is a small observation ledger, not a live position view, map, waypoint,
or prediction system. Records are immutable; native publication is the only
writer used by the transactional Spot adapter.
"""
from dataclasses import dataclass
import math

from spatial.state import CartesianPosition


@dataclass(frozen=True)
class BeingLocationObservation:
    id: str
    observer_id: str
    being_id: str
    source_action_id: str
    encounter_id: str
    boundary: int
    time: float
    position: CartesianPosition
    basis: str = 'successful_deliberate_spot'

    def __post_init__(self):
        if not all(type(value) is str and value.strip() for value in
                   (self.id, self.observer_id, self.being_id,
                    self.source_action_id, self.encounter_id)):
            raise ValueError('location observation identities must be nonempty strings')
        if type(self.boundary) is not int or self.boundary < 0:
            raise ValueError('location observation boundary must be a nonnegative integer')
        if type(self.time) not in (int, float) or not math.isfinite(self.time):
            raise ValueError('location observation time must be finite')
        if type(self.position) is not CartesianPosition:
            raise TypeError('location observation requires a native CartesianPosition')
        if self.basis != 'successful_deliberate_spot':
            raise ValueError('unsupported location observation basis')


@dataclass(frozen=True)
class LastSeenLocation:
    """Detached historical answer; its position may no longer be current."""
    observer_id: str
    being_id: str
    position: CartesianPosition
    observed_at: float
    boundary: int
    source_action_id: str
    observation_id: str


class LocationEvidenceLedger:
    """A single observer's immutable-record store with a read-only last-seen API."""
    def __init__(self, observer_id):
        if type(observer_id) is not str or not observer_id.strip():
            raise ValueError('location ledger requires a nonempty observer identity')
        self.observer_id = observer_id
        self._observations = {}

    @property
    def observations(self):
        return tuple(sorted(self._observations.values(),
                            key=lambda row: (row.boundary, row.id)))

    def last_seen_location(self, being_id):
        """Return this owner's latest stored sample without consulting Reality."""
        if type(being_id) is not str or not being_id:
            raise ValueError('Being identity must be a nonempty string')
        matches = (row for row in self._observations.values()
                   if row.observer_id == self.observer_id and row.being_id == being_id)
        row = max(matches, key=lambda value: (value.time, value.boundary, value.id),
                  default=None)
        if row is None:
            return None
        return LastSeenLocation(row.observer_id, row.being_id, row.position, row.time, row.boundary,
                                row.source_action_id, row.id)
