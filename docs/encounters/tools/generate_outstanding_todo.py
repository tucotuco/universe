#!/usr/bin/env python3
"""Regenerate a TODO-only queue from unresolved entries in current issue register.

Run tools/generate_outstanding_todo.py [--check]. To close an issue, change the
register Status line to 'Resolved ...', then regenerate. For new issues, add a
Next action field in the register. No completed issue is included in output.
"""
from __future__ import annotations
from pathlib import Path
import re
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1]
REGISTER=ROOT/'encounters-rule-issues-r60.md'
DEST=ROOT/'encounters-outstanding-todo.md'
RE=re.compile(r'(?ms)^### (ES-\d{3}) — ([^\n]+)\n(.*?)(?=^### |^## |\Z)')
NOW={'ES-041','ES-042','ES-043','ES-044','ES-048'}
DOC={'ES-008','ES-033','ES-047','ES-049','ES-051','ES-052'}
DEFERRED={'ES-045','ES-046'}

def extract_action(body:str)->str:
    for label in ('Next action','Still open','Remedy/test','Issue'):
        m=re.search(r'^- \*\*'+re.escape(label)+r':\*\* (.+)',body,re.M)
        if m: return m.group(1).strip()
    return 'Review the detailed issue and specify the next action.'

def generate(reg:str)->str:
    groups={'Rule decisions':[],'Other documentation and source checks':[],
            'Implementation and regression verification':[],'Deferred design':[]}
    for id,title,body in RE.findall(reg):
        m=re.search(r'^- \*\*Status:\*\*\s*(.*)$',body,re.M)
        if not m:
            raise ValueError(f'{id} missing Status')
        status=re.sub(r'\*','',m.group(1).split('·')[0]).strip()
        if status.lower().startswith('resolved'):
            continue
        # Explicit scope-limited completion: defer unaddressed areas in separate issue IDs.
        if id in {'ES-016','ES-019','ES-038','ES-013','ES-015'}:
            continue
        action=extract_action(body)
        if id == 'ES-041':
            action=('Continue the **non-throwing** Being-level force-capacity model in newtons for Pull, Bull rush, leverage, traction, exertion and resultant-force movement; review coupled multiple-grip constraints and remaining Grapple position terminology. Throwing reference geometry and the yd/s velocity formula are adopted in revision 62 (see the [current supplement](encounters-rule-issues-r62.md)); trajectory conventions remain as adopted in revision 60. At implementation time, regression-test calculations and the transition from historical lookup tables; review drag/wind only with launched projectiles.')
        if id in NOW: key='Rule decisions'
        elif id in DOC: key='Other documentation and source checks'
        elif id in DEFERRED: key='Deferred design'
        elif 20<=int(id[-3:])<=30: key='Implementation and regression verification'
        else: key='Other documentation and source checks'
        groups[key].append((id,title,action))
    out=['# Encounters — outstanding to-do (open items only)',
         '', '**Current adopted baseline: revision 61, supplemented on the listed subjects by revision 62.** This outstanding-only list is generated from the historical [revision-60 issue register](encounters-rule-issues-r60.md); the [revision-62 issue supplement](encounters-rule-issues-r62.md) records current throwing-status changes. This list contains **only work not yet completed**.',
         '', 'The list is generated from active issue statuses. Update the issue register first, then run `python tools/generate_outstanding_todo.py`. No entries here constitute an adopted rule.', '']
    for label,items in groups.items():
        if not items: continue
        out.extend(['## '+label,''])
        if label=='Implementation and regression verification':
            out.append('These were identified against an earlier reconstructed Universe code snapshot; **reverify against the current checkout** before making changes.')
            out.append('')
        for id,title,action in items:
            anchor=re.sub('[^a-z0-9-]','',f'{id}--{title}'.lower().replace(' ','-'))
            out.append(f'- [ ] **[{id}](encounters-rule-issues-r60.md#{anchor}) — {title}.** {action}')
        out.append('')
    out.extend(['---','', 'Check for freshness: `python tools/generate_outstanding_todo.py --check`.',''])
    return '\n'.join(out)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true');args=ap.parse_args()
    rendered=generate(REGISTER.read_text())
    if args.check:
        if not DEST.exists() or DEST.read_text()!=rendered:
            print('Outstanding to-do is stale; regenerate it.',file=sys.stderr);return 1
        print('Outstanding to-do current');return 0
    DEST.write_text(rendered);print('Regenerated',DEST);return 0
if __name__=='__main__': sys.exit(main())
