"""EXPERIMENTAL Group sensor: bounded exploration of a traveling caravan.

Run: python examples/interactive_discovery.py
     python examples/interactive_discovery.py --seed 392
     python examples/interactive_discovery.py --commands 'look;ask childhood;notes;quit'
     python examples/interactive_discovery.py --commands 'ask childhood;quit' --audit

Only --audit grants out-of-world access to objective facts. Normal commands
operate through Encounter Actions and the explorer's retained evidence.
This is a command-line experiment, not a natural-language/dialogue model.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from group_observation import ObserveGroupAction
from history_conversation import AskAboutPastAction
from integrated_discovery import advance_with_group, prepare_scenario, propose_childhood


TOPICS = {
    'childhood': (10, 'early_running'),
    'later': (20, 'later_running'),
}
CATEGORIES = ('humans', 'livestock', 'dogs')


class ExplorerSession:
    """A player-command boundary with no routine access to objective history.

    The scene retains the authoritative world. Only ``developer_audit()``
    explicitly reads objective episode facts, outside the normal command API.
    Commands return text so a terminal, a test, or a later UI can use them.
    """

    def __init__(self, seed=391):
        self.scene = prepare_scenario(seed)
        self.seed = seed
        self.following = True
        self.closed = False
        self.sequence = 0
        self.observations = []
        self.questions = []
        self.topic_asks = defaultdict(int)

    @property
    def time(self):
        return self.scene['encounter'].time

    def _advance(self, duration=1):
        advance_with_group(self.scene, duration, follow=self.following)

    def _look(self):
        encounter = self.scene['encounter']
        observer, herder, group = (self.scene[k] for k in
                                   ('observer', 'herder', 'group'))
        # The existing range proxy provides awareness; it is not optical LOS.
        noticed = encounter.perceive_within(observer.id, 1000)
        ids = {perceived.target_id for perceived in noticed}
        people = 'a traveling herder' if herder.id in ids else 'no nearby person'
        caravan = 'a caravan' if group.id in ids else 'no nearby caravan'
        mode = ('traveling alongside' if self.following
                else 'staying where you are as the caravan moves')
        return f'Time {self.time:g}: You notice {people} and {caravan}. You are {mode}.'

    def _observe(self, category):
        if category not in CATEGORIES:
            return 'Choose a count to observe: humans, livestock, or dogs.'
        world, encounter, observer, group, config, belief = (
            self.scene[k] for k in
            ('world', 'encounter', 'observer', 'group', 'config', 'belief'))
        self.sequence += 1
        action = ObserveGroupAction(
            world, observer.id, group.id, encounter.time, seed=self.seed,
            random_key=f'explorer-observation-{self.sequence}',
            focus_category=category,
            observation=config['action_observation']['sensor'],
            interpretation=config['interpretation'],
            experience={'success': 12, 'failure': 18}, ledger=belief)
        encounter.schedule_action(action)
        self._advance()
        self.observations.append(action)
        if action.field_observation is None:
            return f'Observation attempted at time {action.end_time:g}: {action.resolution.outcome}; no count evidence acquired.'
        # Display the interpreted estimate; neither the controller nor its
        # output reads Group.counts() or the underlying objective ledger.
        interpretation = belief.reports_for_observation(action.field_observation.id)
        report = interpretation[category]
        return (f'Observation {len(belief.evidence)} at time {action.end_time:g}: '
                f'estimated {category} {report.estimate} '
                f'(reported interval {report.interval[0]}–{report.interval[1]}).')

    def _ask(self, topic_alias):
        if topic_alias not in TOPICS:
            return 'Choose a topic: childhood or later.'
        time, topic = TOPICS[topic_alias]
        world, encounter, observer, herder = (
            self.scene[k] for k in ('world', 'encounter', 'observer', 'herder'))
        # A scripted second account is inconsistent with the first. This is an
        # experimental response policy, NOT a model of deception or memory.
        repeated = self.topic_asks[topic_alias] > 0
        action = AskAboutPastAction(
            world, observer.id, herder.id, encounter.time,
            episode_time=time, topic=topic,
            generate=propose_childhood(self.seed, topic, episode_time=time),
            substituted_claim=(
                'I learned to run entirely alone, far from any settlement.'
                if repeated else None),
            received_accounts=self.scene['heard'])
        encounter.schedule_action(action)
        self._advance()
        self.questions.append(action)
        if action.heard_account is None:
            return f'Question attempted at time {action.end_time:g}: {action.resolution.outcome}; no account heard.'
        self.topic_asks[topic_alias] += 1
        return f'Herder, speaking about {topic_alias}: “{action.heard_account.words}”'

    def _notes(self):
        belief = self.scene['belief']
        heard = self.scene['heard']
        lines = ['Your evidence notebook (statements are not verified facts):']
        if not belief.evidence and not heard:
            return '\n'.join(lines + ['  No evidence collected.'])
        for i, evidence in enumerate(belief.evidence, 1):
            current = belief.reports_for_observation(evidence.id)
            counts = ', '.join(
                f'{key} ≈{report.estimate} ({report.interval[0]}–{report.interval[1]})'
                for key, report in current.items())
            lines.append(f'  Observation {i}, time {evidence.time:g}: {counts}')
        for i, account in enumerate(heard, 1):
            alias = next((a for a, (t, topic) in TOPICS.items()
                          if t == account.claimed_time and topic == account.topic),
                         account.topic)
            lines.append(f'  Account {i}, time {account.heard_at:g}, '
                         f'about {alias}: “{account.words}”')
        return '\n'.join(lines)

    def _compare(self):
        lines = ['Comparing your evidence (no objective truth is exposed):']
        heard = self.scene['heard']
        for alias, (time, topic) in TOPICS.items():
            subset = [a for a in heard if a.claimed_time == time and a.topic == topic]
            if len(subset) >= 2:
                if len({a.words for a in subset}) > 1:
                    lines.append(f'  {alias}: conflicting accounts; further inquiry may be warranted.')
                else:
                    lines.append(f'  {alias}: accounts agree; agreement does not prove accuracy.')
        conflicts = self.scene['belief'].discrepancies(self.scene['group'].id)
        for category in sorted({item[0] for item in conflicts}):
            lines.append(f'  {category}: observation intervals conflict.')
        if len(lines) == 1:
            lines.append('  No comparable conflicting evidence yet.')
        return '\n'.join(lines)

    def execute(self, command):
        if self.closed:
            return 'The encounter has ended.'
        if not isinstance(command, str):
            raise TypeError('command must be text')
        parts = command.strip().lower().split()
        if not parts:
            return 'Enter a command, or help to see the options.'
        verb, args = parts[0], parts[1:]
        if verb in ('quit', 'exit') and not args:
            self.closed = True
            return 'You leave the encounter. Unasked questions remain unresolved.'
        if verb == 'help' and not args:
            return ('Commands: look | observe humans|livestock|dogs | '
                    'ask childhood|later | notes | compare | follow on|off | '
                    'wait [1–20] | quit.\n'
                    'Only observation and inquiry can produce new evidence; '
                    'repeating a question may elicit a different account.')
        if verb == 'look' and not args:
            return self._look()
        if verb == 'observe' and len(args) == 1:
            return self._observe(args[0])
        if verb == 'ask' and len(args) == 1:
            return self._ask(args[0])
        if verb == 'notes' and not args:
            return self._notes()
        if verb == 'compare' and not args:
            return self._compare()
        if verb == 'follow' and len(args) == 1 and args[0] in ('on', 'off'):
            self.following = args[0] == 'on'
            return ("You choose to match the caravan motion from your current position." if self.following
                    else 'You choose to stay in place while the caravan travels on.')
        if verb == 'wait' and len(args) <= 1:
            amount = args[0] if args else '1'
            if amount.isascii() and amount.isdigit() and 1 <= int(amount) <= 20:
                self._advance(int(amount))
                return f'Time advances to {self.time:g}. No new questions were asked.'
            return 'Wait must specify an integer between 1 and 20.'
        return 'Unknown command. Type help for available actions.'

    def developer_audit(self):
        """Out-of-world developer tool. Never reachable via ``execute()``."""
        history = self.scene['history']
        rows = ['[Developer audit — not available to the explorer]']
        for alias, (time, topic) in TOPICS.items():
            record = history.inspect_episode(time, topic)
            rows.append(f'  {alias}: ' + ('unresolved' if record is None
                                              else record.value['description']))
        return '\n'.join(rows)


def play(seed=391, *, input_fn=input, output_fn=print, audit=False, commands=None):
    """Interactive terminal (or a scripted test transcript) without truth leakage."""
    session = ExplorerSession(seed)
    output_fn('A caravan passes nearby. You are its explorer, not its author.')
    output_fn(session.execute('help'))
    if commands is None:
        while not session.closed:
            try:
                command = input_fn('Explorer> ')
            except (EOFError, KeyboardInterrupt):
                command = 'quit'
            output_fn(session.execute(command))
    else:
        for command in commands:
            output_fn(f'Explorer> {command}')
            output_fn(session.execute(command))
            if session.closed:
                break
    if audit:
        output_fn(session.developer_audit())
    return session


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=391)
    parser.add_argument('--commands', help='semicolon-separated scripted commands (for testing)')
    parser.add_argument('--audit', action='store_true',
                        help='append out-of-world objective-history inspection')
    options = parser.parse_args()
    play(seed=options.seed,
         commands=None if options.commands is None else options.commands.split(';'),
         audit=options.audit)
