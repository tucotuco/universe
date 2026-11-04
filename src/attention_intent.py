"""Narrow Agent attention-intent adapter for native deliberate Spot.

The adapter accepts no target ID and returns no Action/target identity. Native
developer APIs remain omniscient; this is an owner-facing response boundary,
not a general Python security boundary.
"""
from dataclasses import dataclass

from transactional_progression import mode_of, planning_entry


@dataclass(frozen=True)
class AttentionIntentResult:
    accepted: bool
    status: str


def accept_spot_attention(encounter, actor_id, *, location_ledger=None):
    """Bind one unfamiliar participating Being to an ordinary six-second Spot.

    Zero or multiple candidates produce the same identity-free refusal and do
    not create an Action. A unique target is captured while holding the native
    scheduling lock and is never retargeted during the Spot interval.
    """
    from activities import SpotAction

    if mode_of(encounter) != 'transactional':
        raise ValueError('attention intent requires a selected native transactional Encounter')
    planning_entry(encounter)
    lock = encounter.universe._schedule_lock
    with lock:
        encounter._assert_timeline()
        if mode_of(encounter) != 'transactional':
            raise ValueError('attention intent requires a selected native transactional Encounter')
        if encounter.get_being(actor_id) is None:
            return AttentionIntentResult(False, 'not_accepted')
        if location_ledger is not None:
            from location_observation import LocationEvidenceLedger
            if (type(location_ledger) is not LocationEvidenceLedger
                    or location_ledger.observer_id != actor_id):
                return AttentionIntentResult(False, 'not_accepted')

        known = set(encounter.aware_beings(actor_id))
        candidates = tuple(dict.fromkeys(
            being_id for being_id in encounter.being_list
            if being_id != actor_id
            and being_id not in known
            and encounter.get_being(being_id) is not None
        ))
        if len(candidates) != 1:
            return AttentionIntentResult(False, 'not_accepted')

        target_id = candidates[0]
        action = SpotAction(encounter.universe, actor_id, target_id,
                            encounter.time, location_ledger=location_ledger)
        book = encounter._choice_book
        prior_drafts = set(book._drafts)
        try:
            encounter.schedule_choice((action,))
        except Exception:
            # Native schedule publication is rollback-protected. Do not return
            # diagnostics or leave an open proposal that could disclose the
            # privately bound target through the Agent-facing adapter.
            for draft_id in set(book._drafts) - prior_drafts:
                book._drafts.pop(draft_id, None)
            return AttentionIntentResult(False, 'not_accepted')
        return AttentionIntentResult(True, 'accepted')
