"""Small resolved Encounters R60 grappling test harness, using unchanged R4 fatigue.

Scope: two Medium combatants within reach, known opponents, no injuries/damage,
no movement/terrain, no multi-action, no positional takedown/reverse/pin.
Implements distinct Touch (opposed d20), Grab (opposed 3d6), initial and
continuing Grapple (opposed 3d6), least restrictive Grapple Escape, and
Break hold (Strength contest); seeded independent opposed dice. The state
machine is a *subset* of Encounters, not the complete encounter resolver.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
from random import Random
from universe_physical_fatigue_r4 import State, evolve, peak, critical
from standard_fatigue_check import physical_check_penalty, CHECK_SENSITIVITY
from combat_calibration import effort_for_actor

DEFAULT_COSTS = {
    'touch': {'demand':.56,'wear':1.,'demand_basis':'reference_fitness','fitness_exponent':.35},
    'grab': {'demand':.73,'wear':1.,'demand_basis':'reference_fitness','fitness_exponent':.35},
    'grapple': {'demand':.70,'wear':1.1,'demand_basis':'reference_fitness','fitness_exponent':.35},
    'escape': {'demand':.50,'wear':1.0,'demand_basis':'reference_fitness','fitness_exponent':.35},
    'break_hold': {'demand':.38,'wear':.9,'demand_basis':'reference_fitness','fitness_exponent':.35},
    'recover': {'demand':.08,'wear':.4},
    'rest': {'demand':.05,'wear':.4},
}

def mod(score):
    # Adopted Encounters ability bonuses: standard D&D bonus progression.
    return (score-10)//2

def dice(rng, sides, count):
    return [rng.randint(1,sides) for _ in range(count)]

def fatigue_contest_penalty(state, physiology=None):
    """Universal Q/B penalty, independent of Fitness and physiology.

    physiology is accepted for callers of older test helpers, but ignored:
    only fatigue reserve percentages select the check modifier.
    """
    return physical_check_penalty(state.q, state.b)

def opposed(rng, kind, a, b, actors, intents, states=None, profiles=None, fatigue_enabled=True):
    """Make ONE opposed check; tie never creates a new grapple/grip position."""
    def v(who):
        data=actors[who]; traits=data.get('abilities',{})
        if kind=='touch':
            return (data.get('attack_level',0) if who==a else data.get('defense_level',0)), 'd20'
        if kind=='break_hold':
            return mod(traits.get('strength',10)), '3d6'
        extra=data.get('improved_grapple',0)+max(mod(traits.get('strength',10)),mod(traits.get('dexterity',10)))
        if kind=='grapple' and intents.get(who)=='escape':extra+=data.get('escape_artist',0)
        extra-=data.get('armor_check_penalty',0)
        return extra,'3d6'
    ba,_=v(a);bb,_=v(b)
    penalty_a=fatigue_contest_penalty(states[a]) if fatigue_enabled and states is not None else 0
    penalty_b=fatigue_contest_penalty(states[b]) if fatigue_enabled and states is not None else 0
    ba-=penalty_a;bb-=penalty_b
    n=1 if kind=='touch' else 3
    sides=20 if n==1 else 6
    da=dice(rng,sides,n);db=dice(rng,sides,n)
    va=sum(da)+ba;vb=sum(db)+bb
    return ({'kind':kind,'scores':{a:va,b:vb},'dice':{a:da,b:db},
        'modifiers':{a:ba,b:bb},'fatigue_penalties':{a:penalty_a,b:penalty_b},'winner':a if va>vb else b if vb>va else None})

def validate(scenario):
    g=scenario.get('grapple_encounter')
    if not isinstance(g,dict) or len(scenario.get('actors',{}))!=2:
        raise ValueError('grapple_encounter needs two actors')
    phases=g.get('phases')
    if not isinstance(phases,list) or len(phases)!=3 or [p.get('seconds') for p in phases]!=[180,30,180]:
        raise ValueError('Grappling test requires 180s bout, 30s rest, 180s bout')
    if not isinstance(g.get('seed'),int) or isinstance(g['seed'],bool) or not 0<=g['seed']<=2**31-1:
        raise ValueError('Seed must be an integer 0..2**31-1')
    if not isinstance(g.get('fatigue_contest_penalty_enabled', True),bool):
        raise ValueError('fatigue_contest_penalty_enabled must be boolean')
    # Import migration for R4.7/R4.8: identical rule value 5 is accepted
    # and removed from the configuration. Any non-5 value is rejected.
    for old_key in ('contest_penalty_scale','physical_check_fatigue_sensitivity'):
        if old_key in g:
            if type(g[old_key]) not in (int,float) or g[old_key] != CHECK_SENSITIVITY:
                raise ValueError(f'{old_key} is no longer configurable; fixed physical-check sensitivity is 5')
            g.pop(old_key)
    costs={**DEFAULT_COSTS,**g.get('costs',{})}
    for kind, spec in costs.items():
        if kind not in DEFAULT_COSTS or not isinstance(spec,dict):raise ValueError('unknown grappling effort type')
        d=spec.get('demand')
        if type(d) not in (int,float) or not 0<=d<=1:raise ValueError('grappling demands 0..1')
        w=spec.get('wear',1)
        if type(w) not in (int,float) or not 0<=w<=10:raise ValueError('grappling wear 0..10')
        if spec.get('demand_basis','individual') not in ('individual','reference_fitness'):
            raise ValueError('invalid fixed-demand interpretation')
        if not 0<=spec.get('fitness_exponent',0)<=3:raise ValueError('invalid fitness exponent')
    for name,a in scenario['actors'].items():
        for skill in ('improved_grapple','escape_artist','attack_level','defense_level','armor_check_penalty'):
            if not isinstance(a.get(skill,0),int) or not 0<=a.get(skill,0)<=30:
                raise ValueError(f'{name}: {skill} must be an integer 0..30')
        ab=a.get('abilities',{})
        if not 1<=ab.get('strength',10)<=30 or not 1<=ab.get('dexterity',10)<=30:
            raise ValueError('Strength and Dexterity must be 1..30')
    return costs

def simulate_encounter(cfg, scenario, effective_profile, scaling):
    costs=validate(scenario)
    g=scenario['grapple_encounter'];names=list(scenario['actors']);a0,a1=names
    fatigue_enabled=g.get('fatigue_contest_penalty_enabled',True)
    rng=Random(g['seed']);actors=scenario['actors']
    profiles={n:effective_profile(cfg,actors[n]['profile'],actors[n].get('fitness',12),actors[n].get('run_level',0)) for n in names}
    scales={n:scaling(cfg,actors[n]['profile']) for n in names}
    states={n:State() for n in names};grips={n:False for n in names};touch={n:False for n in names};maint_due={n:None for n in names};first_check_due={n:False for n in names}
    # Controller is the Being whose Grapple action has been established. It is
    # independent of both physical Grabs (which may remain after Escape).
    controller=None; scheduled={n:None for n in names};counts={n:Counter() for n in names};logs=[];points={n:[] for n in names}
    phase_markers=[];global_second=0;ever_failed_action=False;control_history=[]

    def snapshot(n,sec,label,require,actual):
        s=states[n];p=profiles[n]
        points[n].append({'seconds':sec,'q':round(100*s.q,5),'b':round(100*s.b,5),
          'critical':round(100*critical(s.b,p),5),'max_output':round(100*peak(s.q,s.b,p),5),
          'segment':label,'demand':round(100*require,3),'actual':round(100*actual,3),'capped':False})
    for n in names:snapshot(n,0,'Start',0,0)

    def cost(who,kind):
        spec=costs[kind]
        return effort_for_actor(spec,actors[who],scales[who]),spec.get('wear',1)

    def decision(who,other,remaining):
        # No silent lowering of declared requirements. An unaffordable action
        # is not performed; the Being may explicitly elect a different action.
        if remaining<1: return 'rest',1
        if controller==other:
            return 'escape',min(6,remaining)
        if controller==who:
            return 'grapple',min(6,remaining)
        if grips[who]:
            return 'grapple',min(6,remaining)
        if grips[other]:
            return 'break_hold',1
        if not grips[who]:
            return ('grab' if touch[who] else 'touch'),1
        return 'grapple',min(6,remaining)

    def apply_event(results,sec):
        nonlocal controller,ever_failed_action
        # All results assessed from pre-resolution state; apply state changes
        # only after all checks were evaluated.
        old_controller=controller;old_grips=dict(grips);old_touch=dict(touch)
        nxt_grips=dict(grips);nxt_touch=dict(touch);new_ctrl=old_controller
        next_maint=dict(maint_due)
        next_first=dict(first_check_due)
        events=[];results_by={n:z for n,z in results}
        # Separate simultaneous touches and Grabs. Independent contested
        # dice, no same-second bonus from a newly established physical grip.
        for who,z in results:
            other=a0 if who==a1 else a1
            if z['kind']=='touch':
                chk=opposed(rng,'touch',who,other,actors,{},states,profiles,fatigue_enabled)
                if chk['winner']==who:nxt_touch[who]=True
                events.append({'actor':who,'action':'touch','success':chk['winner']==who,'check':chk})
            if z['kind']=='grab':
                if not old_touch[who]:
                    events.append({'actor':who,'action':'grab','success':False,'reason':'no prior successful Touch'})
                else:
                    chk=opposed(rng,'grab',who,other,actors,{},states,profiles,fatigue_enabled)
                    if chk['winner']==who:
                        nxt_grips[who]=True
                        next_maint[who]=sec+6
                        next_first[who]=True
                    nxt_touch[who]=False
                    events.append({'actor':who,'action':'grab','success':chk['winner']==who,'check':chk})
        # Break hold contests: distinct 3d6 + Strength modifier; an Escape
        # never releases these separate physical grips.
        for who,z in results:
            if z['kind']!='break_hold':continue
            other=a0 if who==a1 else a1
            if not old_grips[other]:continue
            chk=opposed(rng,'break_hold',who,other,actors,{},states,profiles,fatigue_enabled)
            if chk['winner']==who:
                nxt_grips[other]=False
                next_maint[other]=None
                next_first[other]=False
            if old_controller==who:new_ctrl=None  # changing action ends own Grapple only
            events.append({'actor':who,'action':'break_hold','success':chk['winner']==who,'check':chk})
        # One shared opposed Grapple check, not one check for each wrestler.
        # If a grapple is established, Escape can end ONLY that Grapple.
        wants={n:z['kind'] for n,z in results_by.items()}
        involved=any(k in ('grapple','escape') for k in wants.values())
        if involved:
            check=opposed(rng,'grapple',a0,a1,actors,wants,states,profiles,fatigue_enabled)
            winner=check['winner']
            if old_controller is None:
                if winner and wants.get(winner)=='grapple' and old_grips[winner]:
                    new_ctrl=winner
            else:
                other=a0 if old_controller==a1 else a1
                if wants.get(other)=='escape' and winner==other:
                    new_ctrl=None
                # unsuccessful / tied Escape preserves previous Grapple state.
            events.append({'action':'grapple-check','check':check,
                'declared':wants,'controller_before':old_controller,'controller_after':new_ctrl})
            if old_controller!=new_ctrl:
                counts[new_ctrl or (a0 if old_controller==a1 else a1)]['control_transitions']+=1
                control_history.append({'second':sec,'from':old_controller,'to':new_ctrl})
        # Individual physical Holds require their own six-second Grab
        # maintenance checks. Only at the FIRST initiating Grapple check
        # coincident with the prerequisite Hold check is the latter replaced.
        for holder in names:
            if not old_grips[holder] or maint_due[holder] is None or sec < maint_due[holder]:continue
            other=a0 if holder==a1 else a1
            if wants.get(holder)=='grapple' and old_controller is None and first_check_due[holder]:
                next_maint[holder]=sec+6
                next_first[holder]=False
                events.append({'actor':holder,'action':'hold-maintenance substituted by initial grapple check'})
                continue
            check=opposed(rng,'grab',holder,other,actors,{},states,profiles,fatigue_enabled)
            keep=check['winner']==holder
            if not keep:
                nxt_grips[holder]=False
                next_maint[holder]=None
            else:next_maint[holder]=sec+6
            counts[holder]['hold maintenance checks']+=1
            events.append({'actor':holder,'action':'hold maintenance','success':keep,'check':check})
        for holder,z in results:
            if z['kind']=='grapple' and old_grips[holder]:next_first[holder]=False
        grips.update(nxt_grips);touch.update(nxt_touch);maint_due.update(next_maint);first_check_due.update(next_first);controller=new_ctrl
        for who,z in results:
            counts[who][z['kind']+' resolved']+=1
        logs.append({'second':sec,'outcome':'opposed check(s) resolved against common snapshot',
                     'events':events,'controller':controller,'grips':dict(grips)})

    for phase in g['phases']:
        label=phase['name'];start=global_second;duration=phase['seconds']
        phase_markers.append({'name':label,'start_s':start,'end_s':start+duration})
        # Before a new bout, the previous bouts' physical Grapples and Grabs
        # are intentionally released by the sport referee. This is an
        # experimental bout boundary, not fatigue recovery.
        if phase.get('kind') in ('bout','rest'):
            controller=None;grips={n:False for n in names};touch={n:False for n in names};maint_due={n:None for n in names};first_check_due={n:False for n in names};first_check_due={n:False for n in names};maint_due={n:None for n in names}
            scheduled={n:None for n in names}
            logs.append({'second':start,'outcome':('rest begins' if phase.get('kind')=='rest' else 'bout begins')+'; grips and Grapple positions released',
                         'events':[],'controller':controller})
        for t in range(1,duration+1):
            sec=start+t;old_states=dict(states);end_actions=[];pending={};action_labels={}
            for n in names:
                other=a0 if n==a1 else a1
                if phase.get('kind')=='rest':
                    kind='rest';scheduled[n]={'kind':kind,'end':sec}
                elif scheduled[n] is None or scheduled[n]['end']<sec:
                    choice,nsec=decision(n,other,duration-t+1)
                    demand,_=cost(n,choice)
                    if demand>peak(old_states[n].q,old_states[n].b,profiles[n])+1e-9:
                        counts[n]['infeasible '+choice]+=1;ever_failed_action=True
                        logs.append({'second':sec,'outcome':'declared action infeasible; actor chooses recovery',
                          'events':[{'actor':n,'action':choice,'required':round(demand,4),
                            'available':round(peak(old_states[n].q,old_states[n].b,profiles[n]),4)}]})
                        choice='recover';nsec=1
                    scheduled[n]={'kind':choice,'end':sec+nsec-1}
                a=scheduled[n];kind=a['kind'];demand,wear=cost(n,kind)
                if demand>peak(old_states[n].q,old_states[n].b,profiles[n])+1e-9:
                    counts[n]['infeasible '+kind]+=1;ever_failed_action=True
                    logs.append({'second':sec,'outcome':'ongoing action infeasible; canceled without completing',
                      'events':[{'actor':n,'action':kind,'required':round(demand,4),
                                'available':round(peak(old_states[n].q,old_states[n].b,profiles[n]),4)}]})
                    kind='recover';demand,wear=cost(n,kind)
                    scheduled[n]={'kind':kind,'end':sec}
                result=evolve(old_states[n],demand,1,profiles[n],wear=wear,max_step=.25)
                # A predicted late-second cap invalidates the attempted action,
                # not the whole encounter. The one-second fallback is explicit.
                if result.capped:
                    counts[n]['infeasible '+kind]+=1;ever_failed_action=True
                    logs.append({'second':sec,'outcome':'action becomes infeasible; not resolved',
                      'events':[{'actor':n,'action':kind}]})
                    kind='recover';demand,wear=cost(n,kind)
                    scheduled[n]={'kind':kind,'end':sec}
                    result=evolve(old_states[n],demand,1,profiles[n],wear=wear,max_step=.25)
                pending[n]=result.state;action_labels[n]=(kind,demand)
                counts[n]['seconds '+kind]+=1
                if scheduled[n]['end']==sec and kind not in ('rest','recover'):
                    end_actions.append((n,{'kind':kind}))
            # Complete actions against shared pre-commit state. Both actors'
            # fatigue consequences become visible only after the resolution.
            if end_actions or (phase.get('kind')=='bout' and any(d is not None and sec>=d for d in maint_due.values())):
                apply_event(end_actions,sec)
            states.update(pending)
            for n in names:
                kind,demand=action_labels[n]
                snapshot(n,sec,label+' / '+kind,demand,demand)
        global_second+=duration
    outputs={}
    for n in names:
        p=profiles[n];s=states[n];a=actors[n]
        outputs[n]={'points':points[n], 'summary':{
            'q':round(100*s.q,2),'b':round(100*s.b,2),'critical':round(100*critical(s.b,p),2),
            'max_output':round(100*peak(s.q,s.b,p),2),
            'check_penalty':physical_check_penalty(s.q,s.b) if fatigue_enabled else 0,
            'total_seconds':global_second,'planned_seconds':global_second,'completed':True,
            'failed_segment':None,'first_infeasible_interval_start_s':None,
            'first_all_out_interval_start_s':None,'work_pace_percent':None,'schedule_delay_seconds':0,
            'events_by_type':dict(counts[n]),'ready_defense':None},
            'being':{'fitness':a.get('fitness',12),'run_level':a.get('run_level',0),
                  'abilities':a.get('abilities',{}),'profile':a['profile']},
            'effective_parameters':asdict(p),'workload_scaling':scales[n]}
    return {'scenario':'','title':scenario.get('title','Resolved Grapple'),
      'description':scenario.get('description',''),
      'assessment_kind':'grapple_encounter_subset',
      'assessment_note':scenario.get('assessment_note',''),
      'objective':None,'actors':outputs,
      'combat':{'mode':'opposed_grapple','phases':phase_markers,'event_log':logs,
                'first_failure':None,'scheduled_seconds':global_second,'elapsed_seconds':global_second,
                'injuries_disabled':True,'attack_rolls_disabled':False,'contests_disabled':False,
                'grappling_position':controller,'physical_grips':dict(grips),
                'control_history':control_history,'seed':g['seed'],
                'fatigue_contest_penalty_enabled':g.get('fatigue_contest_penalty_enabled',False),
                'physical_check_fatigue_sensitivity':CHECK_SENSITIVITY,
                'limitations':'Least-restrictive Grapple only; no pin/takedown/reverse, movement, wounds or armor damage; recovery action choices are test policies; Q/B-only physiology.',
                'had_infeasible_actions':ever_failed_action,
                'workload_calibration':'illustrative .70 grapple control demand retained; not measured energetics'}}
