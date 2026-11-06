"""Observer-owned evidence from a successful native Spot of an Object.

This records only the Object identity, its common-snapshot position, and an
optional native projectile-flight status. It is historical evidence, not live
Reality, a Belief model, or a prediction of the Object's later position.
"""
from dataclasses import dataclass
import math

from spatial.state import CartesianPosition


@dataclass(frozen=True)
class ObjectObservation:
    id: str
    observer_id: str
    object_id: str
    source_action_id: str
    encounter_id: str
    boundary: int
    time: float
    position: CartesianPosition
    projectile_status: str | None = None
    basis: str = 'successful_deliberate_spot'

    def __post_init__(self):
        if not all(type(value) is str and value.strip() for value in
                   (self.id, self.observer_id, self.object_id,
                    self.source_action_id, self.encounter_id)):
            raise ValueError('Object observation identities must be nonempty strings')
        if type(self.boundary) is not int or self.boundary < 1:
            raise ValueError('Object observation boundary must be a positive integer')
        if type(self.time) not in (int, float) or not math.isfinite(self.time):
            raise ValueError('Object observation time must be finite')
        if type(self.position) is not CartesianPosition:
            raise TypeError('Object observation requires a native CartesianPosition')
        if (self.projectile_status is not None
                and (type(self.projectile_status) is not str
                     or self.projectile_status not in ('in_flight', 'landed'))):
            raise ValueError('unsupported native projectile status observation')
        if type(self.basis) is not str or self.basis != 'successful_deliberate_spot':
            raise ValueError('unsupported Object observation basis')


class ObjectObservationLedger:
    """A single observer's append-only Object evidence store."""

    def __init__(self, observer_id):
        if type(observer_id) is not str or not observer_id.strip():
            raise ValueError('Object observation ledger requires an observer identity')
        self.observer_id = observer_id
        self._observations = {}

    @property
    def observations(self):
        return tuple(sorted(self._observations.values(),
                            key=lambda row: (row.boundary, row.id)))

    def last_observation(self, object_id):
        """Return this observer's latest historical sample; never reads Reality."""
        if type(object_id) is not str or not object_id:
            raise ValueError('Object identity must be a nonempty string')
        return max((row for row in self._observations.values()
                    if row.observer_id == self.observer_id
                    and row.object_id == object_id),
                   key=lambda row: (row.time, row.boundary, row.id), default=None)
