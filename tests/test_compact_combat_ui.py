"""Protect the compact UI layout and observer-filtered marker summaries."""
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from tactical_duel import TacticalDuel


class Layout(HTMLParser):
    def __init__(self):
        super().__init__()
        self.path = []
        self.nodes = []
        self.ids = {}
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        parent = self.path[-1] if self.path else None
        if a.get('id'):
            self.ids[a['id']] = (tag, tuple(self.path))
        if tag == 'button':
            self.buttons.append((a, tuple(self.path)))
        self.nodes.append((tag, a, parent))
        if tag not in ('input', 'meta', 'link', 'br', 'hr'):
            self.path.append((tag, a.get('class', ''), a.get('id', '')))

    def handle_endtag(self, tag):
        for i in range(len(self.path) - 1, -1, -1):
            if self.path[i][0] == tag:
                del self.path[i:]
                return


def parse():
    html = (ROOT / 'examples/live_combat_template.html').read_text()
    parsed = Layout()
    parsed.feed(html)
    return html, parsed


class TestCompactCombatUI(unittest.TestCase):
    def test_history_directly_under_map_in_left_column(self):
        _, parsed = parse()
        map_ancestors = parsed.ids['map'][1]
        history_ancestors = parsed.ids['history'][1]
        self.assertTrue(any('encounter-column' in cl for _, cl, _ in map_ancestors))
        self.assertTrue(any('encounter-column' in cl for _, cl, _ in history_ancestors))
        self.assertLess(next(i for i, (tag, attrs, _) in enumerate(parsed.nodes)
                             if attrs.get('id') == 'map'),
                        next(i for i, (tag, attrs, _) in enumerate(parsed.nodes)
                             if attrs.get('id') == 'history'))
        self.assertFalse(any('controls-panel' in cl for _, cl, _ in history_ancestors))

    def test_right_panel_contains_only_buttons_not_state_or_inputs(self):
        _, parsed = parse()
        # State data and effort inputs live in dialogs, not the control panel.
        for control_id in ('efforts', 'effortStatus', 'beingFields', 'scrub',
                           'perception', 'rangeStatus', 'history'):
            self.assertFalse(any('controls-panel' in cl
                                 for _, cl, _ in parsed.ids[control_id][1]))
        self.assertTrue(any('controls-panel' in cl
                            for _, cl, _ in parsed.ids['editEffort'][1]))
        self.assertTrue(any('controls-panel' in cl
                            for _, cl, _ in parsed.ids['save'][1]))

    def test_marker_hover_contains_only_short_observer_safe_summary(self):
        html, _ = parse()
        self.assertIn("group.appendChild(svg('title',{},hoverText", html)
        self.assertIn('HP: ${hp}', html)
        self.assertIn('Actions: ${actions.join', html)
        self.assertIn('Resolves: ${resolutions.join', html)
        self.assertIn("known=own||data.audit", html)
        self.assertIn("'unknown / unknown'", html)
        self.assertIn("b.apparent_action||'Unknown'", html)
        # Server never supplies precise objective foe state in normal view.
        duel = TacticalDuel(17)
        view = duel.state()
        if view['foe']:
            self.assertIsNone(view['foe']['hp'])
            self.assertNotIn('hp_max', view['foe'])
            self.assertNotIn('pending', view['foe'])

    def test_click_dialog_and_effort_dialog_remain_available(self):
        html, parsed = parse()
        self.assertIn('beingDetails', parsed.ids)
        self.assertIn('effortDetails', parsed.ids)
        self.assertIn('editEffort', parsed.ids)
        self.assertIn('closeEffort', parsed.ids)
        self.assertIn('openBeingDetails', html)
        self.assertIn("$('effortDetails').showModal()", html)
        self.assertIn('ArrowUp', html)

    def test_ui_only_no_simulation_change(self):
        duel = TacticalDuel(17)
        before = duel._journal_signature()
        state = duel.state()
        self.assertEqual(before, duel._journal_signature())
        self.assertEqual(state['time'], 0)


if __name__ == '__main__':
    unittest.main()
