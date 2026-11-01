"""Config-driven Encounters action-timeline FATIGUE calibration (no hit/injury dice).

The authoritative R4 fatigue engine is untouched. Actions are declared in YAML,
assigned their specified preparation durations, and committed as a batch at the
end of each second. Combat outcomes, skill contests, positions, and damage are
intentionally NOT modeled: encounter scripts are controlled drills with assumed
legal actions, suitable for isolating fatigue response.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from math import isfinite
from pathlib import Path
import yaml
from universe_physical_fatigue_r4 import State, evolve, peak, critical

def effort_for_actor(action, actor, scaling):
    value=float(action['demand'])
    basis=action.get('demand_basis','individual')
    if basis=='reference_fitness':
        exponent=action.get('fitness_exponent')
        if exponent is None: exponent=scaling['fitness_exponent']
        value *= (scaling['reference_fitness']/float(actor.get('fitness',12)))**exponent
    elif basis!='individual':
        raise ValueError('Combat demand_basis must be individual or reference_fitness')
    if not 0<=value<=1 or not isfinite(value):
        raise ValueError('Combat prescribed output outside [0,1] after Fitness scaling')
    return value

ACTION_SCHEMA=yaml.safe_load((Path(__file__).resolve().parent/'combat-action-schema.yaml').read_text(encoding='utf8'))
if ACTION_SCHEMA.get('schema_version')!=1:raise RuntimeError('Unknown combat action schema')
ACTION_CATALOG=ACTION_SCHEMA['actions']


def duration(spec):
    kind=spec.get('kind')
    if kind not in ACTION_CATALOG:
        raise ValueError(f'Unsupported combat action {kind!r}')
    entry=ACTION_CATALOG[kind];timing=entry['timing']
    if timing in ('weapon','weapon_minus_one'):
        wt=spec.get('weapon_timing_s')
        if type(wt) is not int or wt<2 or wt>30:
            raise ValueError(f'{kind}: weapon_timing_s must be an integer 2..30')
        return wt if timing=='weapon' else wt-1
    if timing=='fixed':
        return entry['seconds']
    if timing=='authored':
        seconds=spec.get('seconds')
        if type(seconds) is not int or seconds<1 or seconds>1200:
            raise ValueError(f'{kind}: authored seconds must be integer 1..1200')
        return seconds
    raise ValueError(f'{kind}: unsupported timing schema {timing}')


def validate_case(scenario):
    c=scenario.get('combat')
    if not isinstance(c,dict) or not c.get('phases') or len(c['phases'])>12:
        raise ValueError('combat requires 1..12 phases')
    actors=scenario['actors']
    if len(actors)!=2:
        raise ValueError('Combat calibration requires exactly two Beings')
    total=0
    for p in c['phases']:
        seconds=p.get('seconds')
        if type(seconds) is not int or seconds<1 or seconds>86400:
            raise ValueError('Combat phase seconds must be positive integers')
        total+=seconds
        programs=p.get('programs')
        if not isinstance(programs,dict) or set(programs)!=set(actors):
            raise ValueError('Each phase needs one action program per combatant')
        for who, pattern in programs.items():
            if not isinstance(pattern,list) or not 1<=len(pattern)<=30:
                raise ValueError(f'{who}: action pattern must contain 1..30 actions')
            for action in pattern:
                if not isinstance(action,dict):raise ValueError('Action must be a mapping')
                duration(action)
                for field,low,high in [('demand',0,1),('wear',0,10)]:
                    value=action.get(field, 1 if field=='wear' else None)
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or not low<=value<=high:
                        raise ValueError(f'{who}: {field} must be between {low} and {high}')
                if 'fitness_exponent' in action and (not isinstance(action['fitness_exponent'],(int,float)) or not 0<=action['fitness_exponent']<=3):
                    raise ValueError('Invalid combat Fitness sensitivity')
                if action.get('demand_basis','individual') not in ('individual','reference_fitness'):
                    raise ValueError('Unrecognized combat demand basis')
                if action['kind']=='rest' and action['demand']>0.25:
                    raise ValueError('Rest is not high-intensity activity')
        for who, initial in p.get('initial',{}).items():
            if who not in actors or not isinstance(initial,list):
                raise ValueError('Initial preparation must list actions for a known actor')
            if sum(duration(x) for x in initial) >= seconds:
                raise ValueError('Initial actions must leave time for the phase program')
            for x in initial:
                if 'fitness_exponent' in x and (not isinstance(x['fitness_exponent'],(int,float)) or not 0<=x['fitness_exponent']<=3):
                    raise ValueError('Invalid initial combat Fitness sensitivity')
                if x.get('demand_basis','individual') not in ('individual','reference_fitness'):
                    raise ValueError('Unrecognized initial action demand basis')
                if not isinstance(x.get('demand'),(int,float)) or not 0<=x['demand']<=1:
                    raise ValueError('Initial action demand must be 0..1')
                if not isinstance(x.get('wear',1),(int,float)) or not 0<=x.get('wear',1)<=10:
                    raise ValueError('Initial action wear must be 0..10')
    if total>14400:raise ValueError('Combat calibration limited to 4 hours')
    return total


def schedule_phase(pattern,offset,seconds):
    """No undeclared parallel non-movement actions or automatic action compression.

    A final unfinished action is canceled at a phase boundary; effort before
    cancellation still counts. The absence of a completion is logged.
    """
    events=[];cursor=0;i=0
    while cursor<seconds:
        step=pattern[i%len(pattern)]
        n=duration(step)
        end=min(seconds,cursor+n)
        events.append({'start':offset+cursor,'end':offset+end,
                       'resolves':end==cursor+n,'kind':step['kind'],
                       'name':step.get('name',step['kind']),
                       'demand':step['demand'],'demand_basis':step.get('demand_basis','individual'),'fitness_exponent':step.get('fitness_exponent',None),'wear':step.get('wear',1),
                       'weapon_timing_s':step.get('weapon_timing_s')})
        cursor=end;i+=1
    return events


def simulate_combat(cfg, scenario, effective_profile, workload_scaling):
    total=validate_case(scenario)
    names=list(scenario['actors']);phases=scenario['combat']['phases']
    schedules={name:[] for name in names};offset=0;markers=[]
    for ph in phases:
        markers.append({'name':ph['name'],'start_s':offset,'end_s':offset+ph['seconds']})
        for name in names:
            initial=ph.get('initial',{}).get(name,[])
            start=offset
            for x in initial:
                end=start+duration(x)
                schedules[name].append({'start':start,'end':end,'resolves':True,
                    'kind':x['kind'],'name':x.get('name',x['kind']),
                    'demand':x['demand'],'demand_basis':x.get('demand_basis','individual'),'fitness_exponent':x.get('fitness_exponent',None),'wear':x.get('wear',1),
                    'weapon_timing_s':x.get('weapon_timing_s')})
                start=end
            schedules[name].extend(schedule_phase(ph['programs'][name],start,offset+ph['seconds']-start))
        offset+=ph['seconds']
    states={n:State() for n in names}
    profiles={n:effective_profile(cfg,a['profile'],a.get('fitness',12),a.get('run_level',0)) for n,a in scenario['actors'].items()}
    pointers={n:0 for n in names}
    counters={n:Counter() for n in names};warnings=[];points={n:[] for n in names}
    ready={n:None for n in names};logs=[];first_failure=None
    # Every non-movement action ending in second t is evaluated using the same
    # t-1 state. All Q/B updates are then committed for the following second.
    for n in names:
        pp=profiles[n]
        points[n].append({'seconds':0,'q':100.,'b':100.,'critical':round(100*critical(1,pp),5),
                          'max_output':100.,'segment':'Start','demand':0.,'actual':0.,'capped':False})
    for second in range(1,total+1):
        actions={};next_states={};failures=[]
        for name in names:
            a=schedules[name][pointers[name]]
            if second-1>=a['end']:
                pointers[name]+=1;a=schedules[name][pointers[name]]
            actions[name]=a
            p=profiles[name]
            st=states[name]
            req=effort_for_actor(a,scenario['actors'][name],workload_scaling(cfg,scenario['actors'][name]['profile']))
            if req>peak(st.q,st.b,p)+1e-9:
                failures.append({'actor':name,'second':second,'action':a['name'],
                                 'required':round(req,4),'available':round(peak(st.q,st.b,p),4)})
                continue
            result=evolve(st,req,1,p,wear=a['wear'],max_step=.25)
            if result.capped:
                failures.append({'actor':name,'second':second,'action':a['name'],
                                 'required':round(req,4),'available':round(peak(st.q,st.b,p),4)})
            next_states[name]=result.state
        if failures:
            first_failure=failures
            logs.append({'second':second,'outcome':'prescribed action infeasible', 'events':failures})
            break
        # Resolve predeclared action completions and ready defenses against
        # the common snapshot. No wounds/damage/disarming or skill rolls.
        completing=[]
        for name,a in actions.items():
            if a['end']==second:
                if a['resolves']:
                    completing.append((name,a))
                else:
                    counters[name]['canceled at phase boundary']+=1
        defenses=[]
        for name,a in completing:
            counters[name][a['kind']]+=1
            if a['kind'] in ('parry','dodge'):
                ready[name]=a['kind']
            elif a['kind']=='strike':
                # An attack by the same weapon forfeits an unspent ready Parry.
                if ready[name]=='parry':ready[name]=None
        for name,a in completing:
            if a['kind']!='strike':continue
            other=next(x for x in names if x!=name)
            if ready[other]:
                defenses.append({'defender':other,'defense':ready[other],
                                 'against':name,'second':second})
                counters[other]['defenses applied']+=1
                ready[other]=None
        if completing or defenses:
            logs.append({'second':second,'outcome':'action preparations completed (no hit/contest rolls)',
                         'events':[{'actor':name,'action':a['name'],'kind':a['kind']} for name,a in completing],
                         'defenses':defenses})
        # Commit ALL state updates together at end-of-second.
        states.update(next_states)
        for name,a in actions.items():
            s=states[name];p=profiles[name]
            effective=effort_for_actor(a,scenario['actors'][name],workload_scaling(cfg,scenario['actors'][name]['profile']))
            points[name].append({'seconds':second,'q':round(100*s.q,5),
                'b':round(100*s.b,5),'critical':round(100*critical(s.b,p),5),
                'max_output':round(100*peak(s.q,s.b,p),5),
                'segment':a['name'],'demand':round(100*effective,4),
                'actual':round(100*effective,4),'capped':False})
    elapsed=points[names[0]][-1]['seconds']
    results={}
    for name in names:
        a=scenario['actors'][name];s=states[name];p=profiles[name]
        results[name]={'points':points[name],
             'summary':{'q':round(s.q*100,2),'b':round(s.b*100,2),
                  'critical':round(critical(s.b,p)*100,2),
                  'max_output':round(peak(s.q,s.b,p)*100,2),
                  'total_seconds':elapsed,'planned_seconds':total,
                  'completed':first_failure is None,
                  'failed_segment':first_failure[0]['action'] if first_failure else None,
                  'first_infeasible_interval_start_s':elapsed if first_failure else None,
                  'first_all_out_interval_start_s':None,
                  'work_pace_percent':None,'schedule_delay_seconds':0,
                  'events_by_type':dict(counters[name]),
                  'ready_defense':ready[name],
                  'first_failure':first_failure},
             'being':{'fitness':a.get('fitness',12),'run_level':a.get('run_level',0),
                      'abilities':a.get('abilities',{}),'profile':a['profile']},
             'effective_parameters':{k:getattr(p,k) for k in p.__dataclass_fields__},
             'workload_scaling':workload_scaling(cfg,a['profile'])}
    return {'scenario':'','title':scenario.get('title','Combat calibration'),
       'description':scenario.get('description',''),
       'assessment_kind':'combat_action_fatigue_calibration',
       'assessment_note':scenario.get('assessment_note',''),
       'objective':None,'actors':results,
       'combat':{'phases':markers,'event_log':logs,
                 'first_failure':first_failure,'scheduled_seconds':total,
                 'elapsed_seconds':elapsed,'injuries_disabled':True,
                 'attack_rolls_disabled':True,'contests_disabled':True,
                 'workload_calibration':'illustrative; not an empirical measurement'}}
