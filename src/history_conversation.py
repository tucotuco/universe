"""Encounter-scoped inquiry into a Being's previously unresolved life.

This is a minimal conversation/observation bridge, not a language, hearing,
truthfulness, psychology, or belief engine. The statement is perceived evidence
of what was said, *not* objective evidence that the claim is true. Resolving
objective history is delegated to the Being's authoritative PersonalHistory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math

from action import Action
from experience import ActionResolution
from perception import Perception


@dataclass(frozen=True)
class HeardAccount:
    """Listener-accessible record of spoken words, not their truth value."""

    action_id: str
    listener_id: str
    speaker_id: str
    heard_at: float
    claimed_time: float
    topic: str
    words: str
    mode: str = 'heard_account_range_scaffold'

    def to_dict(self):
        return asdict(self)


class AskAboutPastAction(Action):
    """Ask an encountered Being for an account of one past episode.

    ``generate(history, reality_view)`` proposes personal-history Facts. It runs
    only if the episode remains unresolved AND the exchange can occur. A
    substituted claim demonstrates an inaccurate account without inferring
    intentional deception. No listener belief is created automatically.
    """

    def __init__(self, universe, listener_id, speaker_id, start_time, *,
                 episode_time, topic, generate, duration=1, max_distance=10,
                 substituted_claim=None, received_accounts=None):
        if listener_id == speaker_id:
            raise ValueError('a Being cannot interview itself')
        for label, value in (('start_time', start_time), ('episode_time', episode_time),
                             ('duration', duration), ('max_distance', max_distance)):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value)):
                raise ValueError(f'{label} must be finite')
        if duration <= 0 or max_distance <= 0:
            raise ValueError('duration and max_distance must be positive')
        if episode_time > start_time:
            raise ValueError('cannot ask about a future episode')
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError('topic must be nonempty')
        if not callable(generate):
            raise TypeError('generate must be callable')
        if substituted_claim is not None and (not isinstance(substituted_claim, str)
                                              or not substituted_claim.strip()):
            raise ValueError('substituted_claim must be a nonempty string')
        if received_accounts is not None and not isinstance(received_accounts, list):
            raise TypeError('received_accounts must be a list or None')
        super().__init__(universe, start_time, None, 'ask_about_past',
                         listener_id, speaker_id, None)
        self.end_time = start_time + duration
        if not math.isfinite(self.end_time):
            raise ValueError('end_time must be finite')
        self.episode_time = episode_time
        self.topic = topic
        self.generate = generate
        self.max_distance = float(max_distance)
        self.substituted_claim = substituted_claim
        self.received_accounts = received_accounts
        self._encounter = None
        self._pending_account = None
        self.heard_account = None
        self.newly_realized = None

    def on_schedule(self, encounter):
        if self._encounter is not None or self.start_time != encounter.time:
            raise ValueError('inquiry must begin once at Encounter current time')
        if encounter.get_being(self.actor_id) is None:
            raise ValueError('listener must participate in Encounter')
        speaker = encounter.get_being(self.target_id)
        if speaker is None or speaker.personal_history is None:
            raise ValueError('speaker must be a participating Being with personal history')
        if not encounter.is_aware(self.actor_id, self.target_id):
            raise ValueError('listener must be aware of speaker before asking')
        speaker.personal_history.episode_key(self.episode_time, self.topic)
        self._encounter = encounter

    def resolve(self, difficulty_class):
        if self._encounter is None:
            raise RuntimeError('inquiry must be scheduled first')
        distance = self._encounter.distance_between_beings(self.actor_id, self.target_id)
        if distance is None:
            return ActionResolution('unplaced')
        if distance > self.max_distance:
            return ActionResolution('out_of_range')
        if not self._encounter.is_aware(self.actor_id, self.target_id):
            return ActionResolution('not_aware')
        speaker = self._encounter.get_being(self.target_id)
        history = speaker.personal_history
        found = history.realize_episode(
            self.episode_time, self.topic,
            lambda view: self.generate(history, view))
        description = found.record.value['description']
        words = description if self.substituted_claim is None else self.substituted_claim
        self._pending_account = HeardAccount(
            self.id, self.actor_id, self.target_id, self.end_time,
            self.episode_time, self.topic, words)
        self.newly_realized = found.newly_realized
        return ActionResolution('heard', observations=(Perception(
            self.actor_id, self.target_id, 'heard_account_range_scaffold',
            distance, self.max_distance),))

    def on_completed(self, encounter):
        # The testimony enters the listener's evidence only once the Encounter
        # has accepted completion and its observation consequences.
        if self.resolution is not None and self.resolution.outcome == 'heard':
            self.heard_account = self._pending_account
            if self.received_accounts is not None:
                self.received_accounts.append(self.heard_account)

    def to_json(self):
        payload = json.loads(super().to_json())
        payload.update({'episode_time': self.episode_time, 'topic': self.topic,
                        'max_distance': self.max_distance,
                        'heard_account': (None if self.heard_account is None
                                          else self.heard_account.to_dict()),
                        'newly_realized': self.newly_realized})
        return json.dumps(payload, indent=2)
