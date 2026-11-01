"""Generate physical-fatigue paper reference cards from the very same R4 engine.

No hard-coded number of tables, physiological type or Fitness range. This
is a case-specific view of Q/B equations, not a separate tabletop model.
"""
from __future__ import annotations
import argparse
import yaml
from universe_physical_fatigue_r4 import State, evolve
from standard_fatigue_check import CHECK_SENSITIVITY


def make_card(cfg, scenario_name, actor_name):
    from workbench import validated_config, effective_profile, workload_scaling
    from combat_calibration import effort_for_actor
    validated_config(cfg)
    if scenario_name not in cfg['scenarios']:
        raise ValueError('Unknown scenario')
    scenario=cfg['scenarios'][scenario_name]
    if actor_name not in scenario['actors']:
        raise ValueError('Unknown actor')
    a=scenario['actors'][actor_name]
    p=effective_profile(cfg,a['profile'],a.get('fitness',12),a.get('run_level',0))
    scale=workload_scaling(cfg,a['profile'])
    g=scenario.get('grapple_encounter',{})
    if not g:
        raise ValueError('Manual action cards are currently available only for the resolved Grapple scenario; other activity tables await workload-card calibration')
    out=[f'# Manual physical-fatigue card — {actor_name}', '',
        f'Scenario: **{scenario_name}** · Physiological profile: **{a["profile"]}** · Fitness: **{a.get("fitness",12)}**',
        f'Physical Check Fatigue Sensitivity (rules constant): **{CHECK_SENSITIVITY}**',
        '', 'Record only **Q%** and **B%**. Both begin at 100% when fully rested. The contest modifier is derived when needed; do not track it separately.',
        '', '## Physical-check penalty — one universal table',
        '', 'Use the **single shared** table supplied in `FATIGUE-CONTEST-TABLE.md` (also available as `fatigue-contest-table-universal.csv`). It applies to all Beings, Fitness values, skills and physically demanding checks. It is **not repeated here** to avoid printing a new copy for every character.',
        '']
    bands=list(range(100,-1,-10))
    out.extend(['','## Action and recovery reference cards', '',
         'Each cell gives **resulting Q% / resulting B%** after completing one prescribed activity interval (Q shown to 0.1%, B to 0.01%).',
         '**X** means the required activity cannot be sustained for that entire interval; change action or resolve the inability, never lower a mandatory demand silently.',
         'Use the nearest listed Q/B starting band for routine paper play. This approximates the continuous trajectory; for critical events, refine the interval or use the digital engine. **Do not repeatedly round B to a whole percent per action:** its small changes would disappear.',
         'For short combat encounters B usually remains near 100%; the first activity card is typically sufficient.',
         ''])
    if g:
        raw=g.get('costs',{})
        choices=[('Touch, 1 s','touch',1),('Grab, 1 s','grab',1),('Grapple, 6 s','grapple',6),('Escape, 6 s','escape',6),('Break hold, 1 s','break_hold',1),('Recover, 6 s','recover',6),('Between-bout rest, 30 s','rest',30)]
        actions=[]
        for title,kind,duration in choices:
            if kind not in raw:continue
            cost=raw[kind];work=effort_for_actor(cost,a,scale)
            actions.append((title,work,cost.get('wear',1),duration))
    for b in (100,75,50,25,0):
        out.extend([f'### Starting B ≈ {b}%', '',
                    '| Starting Q% | '+' | '.join(x[0] for x in actions)+' |',
                    '|'+ '---:|'*(len(actions)+1)])
        for q in bands:
            vals=[]
            for _,work,wear,seconds in actions:
                r=evolve(State(q/100,b/100),work,seconds,p,wear=wear,max_step=.25)
                # Evolve reports cap on any moment when full required effort cannot be maintained.
                if r.capped:
                    vals.append('X')
                else:
                    vals.append(f'{r.state.q*100:.1f}/{r.state.b*100:.2f}')
            out.append('| '+str(q)+' | '+' | '.join(vals)+' |')
        out.append('')
    out.extend(['## Interpretation and limits', '',
         '- Physical Check Fatigue Sensitivity is fixed at **5**. The universal check penalty is independent of Fitness, physiology and activity. No user adjustment or individualized penalty table is required.',
         '- **Action/recovery** costs (not the penalty table) depend on this Being’s Fitness, physiology and configured activity. The custom action card remains experimental; it is not a requirement for using the universal penalty table.',
         '- Use task requirements as given: a required full-effort Grapple is not quietly reclassified as an easier Grapple. Alternative actions must be explicitly legal.',
         '- The percentages shown include small B changes (hundredths of a percentage point). If the group prefers whole-percent tracking, use longer activity blocks or carry fractional changes; do not erase each short interval’s B change.',
         '- Paper rounding should be performed at the end of a meaningful activity block. The digital engine is authoritative for fine-resolution or closely contested cases.',
         '- Long travel and all-day exertion need the appropriate travel-duration cards and cannot be approximated by repeatedly rounding tiny one-second B changes to zero.',
         '', 'This card is an experimental aid generated from Revision 4 physiological parameters, not a new rule system.'])
    return '\n'.join(out)+'\n'

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Generate paper fatigue cards for a Being')
    parser.add_argument('--config',default='config.yaml')
    parser.add_argument('--scenario',default='combat_d_live_grapple')
    parser.add_argument('--actor',default='Grappler Fitness 12')
    parser.add_argument('--output',default='manual-fatigue-card.md')
    args=parser.parse_args()
    cfg=yaml.safe_load(open(args.config,encoding='utf-8'))
    with open(args.output,'w',encoding='utf-8') as f:f.write(make_card(cfg,args.scenario,args.actor))
    print(args.output)
