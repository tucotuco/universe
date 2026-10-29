#!/usr/bin/env python3
"""Universe constrained AI encounter: human actions and autonomous opposition.

    python examples/ai_encounter.py --open
    OPENAI_API_KEY=... python examples/ai_encounter.py --ai openai --model gpt-4.1-mini --open
"""
import argparse
from http.server import HTTPServer
import json
from pathlib import Path
import sys
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'examples')]
from ai_duel import AgentDuel, OpenAIPolicy
from live_combat import make_handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ai', choices=['tactical', 'openai'], default='tactical',
                        help='tactical is deterministic; openai makes real model calls')
    parser.add_argument('--model', default='gpt-4.1-mini', help='model identifier for OpenAI policy')
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--audit', action='store_true',
                        help='developer view revealing hidden opponent state')
    parser.add_argument('--save', type=Path, default=ROOT / 'workspace' / 'ai-encounter.json')
    parser.add_argument('--load', type=Path)
    parser.add_argument('--replay', type=Path)
    args = parser.parse_args(argv)
    if args.load and args.replay:
        parser.error('Choose only one of --load and --replay')
    try:
        policy = (OpenAIPolicy(args.model) if args.ai == 'openai' and not args.replay else None)
    except ValueError as exc:
        parser.error(str(exc))
    source = args.load or args.replay
    if source:
        with source.expanduser().open('r', encoding='utf-8') as stream:
            duel = AgentDuel.from_session(json.load(stream), policy=policy)
    else:
        duel = AgentDuel(args.seed, policy=policy)
    # Existing localhost HTTP surface retains Origin, Host and JSON checks.
    with HTTPServer(('127.0.0.1', args.port), make_handler(
            duel, args.audit, save_path=args.save.expanduser().resolve(),
            replay_only=args.replay is not None,
            template_path=ROOT / 'examples' / 'ai_encounter_template.html')) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print('Universe AI encounter:', url, flush=True)
        print('AI:', args.ai, '(rules-bound suggestions; authoritative Encounter resolves actions)', flush=True)
        if args.ai == 'openai':
            print('Model calls send only the AI opponent’s observation to the OpenAI API.', flush=True)
        print('Stop with Ctrl-C.', flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return duel


if __name__ == '__main__':
    main()
