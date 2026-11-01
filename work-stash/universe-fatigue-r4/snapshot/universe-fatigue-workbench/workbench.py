#!/usr/bin/env python3
"""Local, stdlib HTTP server for the Universe Fatigue Configuration Workbench.

The fatigue engine is vendored verbatim from the Revision 4 reference implementation.
All physics calls are delegated to that module; the workbench only orchestrates scenarios.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, fields
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from math import ceil, isfinite
from pathlib import Path
import sys
import traceback
import yaml

from universe_physical_fatigue_r4 import Profile, State, evolve, peak, critical, human_profile
from combat_calibration import validate_case, simulate_combat
from grapple_encounter import validate as validate_grapple, simulate_encounter

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'static'
CONFIG_PATH = ROOT / 'config.yaml'
FIELD_NAMES = [f.name for f in fields(Profile)]
DEFAULTS = asdict(Profile())
SCHEMA_PATH = ROOT / 'fatigue-schema.yaml'
SCHEMA = yaml.safe_load(SCHEMA_PATH.read_text(encoding='utf-8'))
if set(SCHEMA['parameters']) != set(DEFAULTS):
    raise RuntimeError('Parameter schema does not match the Revision 4 engine Profile fields')
BOUNDS = {key:(p['min'],p['max']) for key,p in SCHEMA['parameters'].items()}
for key,parameter in SCHEMA['parameters'].items():
    parameter['default'] = DEFAULTS[key]

MAX_SEGMENTS = 80
MAX_REPEATS = 2000
MAX_SIM_SECONDS = 30 * 86400
ABILITIES = ('strength','dexterity','constitution','intelligence','wisdom','charisma')
DEFAULT_WORKLOAD_SCALING = {'reference_fitness': 12.0, 'fitness_exponent': 0.0}

def workload_scaling(cfg, name):
    """Inherited reference-Fitness conversion for identical external tasks."""
    ans = dict(DEFAULT_WORKLOAD_SCALING)
    for node in reversed(_profile_chain(cfg, name)):
        overrides = cfg['profiles'][node].get('workload_scaling', {})
        if not isinstance(overrides, dict):
            raise ValueError(f'{node}: workload_scaling must be a mapping')
        for key, value in overrides.items():
            if key not in ans:
                raise ValueError(f'{node}: unknown workload scaling parameter {key}')
            lo, hi = (1, 100) if key == 'reference_fitness' else (0, 3)
            ans[key] = number(value, f'{node}.{key}', lo, hi)
    return ans

def _profile_chain(cfg, name):
    names=[]; seen=set()
    while name:
        if name in seen: raise ValueError(f'Profile inheritance cycle involving {name}')
        seen.add(name); names.append(name)
        if name not in cfg['profiles']: raise ValueError(f'Missing profile: {name}')
        spec=cfg['profiles'][name]
        if not isinstance(spec,dict): raise ValueError(f'{name} profile must be a mapping')
        name=spec.get('parent')
    return names

def locomotion_reference(cfg, name):
    """Optional speed-to-effort calibration, inherited separately from fatigue equations."""
    settings = None
    for node in reversed(_profile_chain(cfg, name)):
        patch = cfg['profiles'][node].get('locomotion')
        if patch is not None:
            if not isinstance(patch, dict): raise ValueError(f'{node}: locomotion must be mapping')
            settings = {**(settings or {}), **patch}
    if settings is None: return None
    for key in ('reference_speed_kmh', 'reference_effort', 'speed_exponent',
                'reference_fitness', 'fitness_exponent'):
        if key not in settings: raise ValueError(f'{name}: missing locomotion.{key}')
    bounds = {'reference_speed_kmh':(1,150),'reference_effort':(.01,1),
              'speed_exponent':(.3,4),'reference_fitness':(1,100),'fitness_exponent':(0,3)}
    for key,(lo,hi) in bounds.items():
        settings[key] = number(settings[key],f'{name}.locomotion.{key}',lo,hi)
    return settings


def segment_duration(segment):
    if 'distance_km' in segment:
        distance=number(segment['distance_km'],'distance_km',.01,1000)
        speed=number(segment.get('speed_kmh'),'speed_kmh',.01,150)
        if 'seconds' in segment:
            raise ValueError('Distance segments derive duration from speed; omit seconds')
        return distance/speed*3600.
    return number(segment.get('seconds'),'seconds',.01,MAX_SIM_SECONDS)


def physical_demand(cfg, actor, segment):
    """Convert authored demand for a reference Being to relative demand for this Being.

    'individual' is the legacy/intensity-choice interpretation: use demand as given.
    'reference_fitness' is an identical external task; the reference_fitness and
    fitness_exponent are both configuration values, not assumptions in the engine.
    """
    if 'distance_km' in segment and segment.get('pace_effort',False):
        locomotion=locomotion_reference(cfg,actor['profile'])
        if locomotion is None: raise ValueError(f"{actor['profile']}: speed-to-effort calibration missing")
        return locomotion['reference_effort'] * (float(segment['speed_kmh']) / locomotion['reference_speed_kmh'])**locomotion['speed_exponent'] * (locomotion['reference_fitness'] / float(actor.get('fitness',12)))**locomotion['fitness_exponent']
    reference=segment['demand']
    basis=segment.get('demand_basis', 'individual')
    if basis == 'individual': return reference
    if basis != 'reference_fitness': raise ValueError(f'Unknown demand basis: {basis}')
    scale=workload_scaling(cfg,actor['profile'])
    fitness=float(actor.get('fitness',12))
    return reference*(scale['reference_fitness']/fitness)**scale['fitness_exponent']



def number(value, label, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f'{label} outside range [{low}, {high}]')
    return float(value)


def validated_config(cfg):
    if not isinstance(cfg, dict) or cfg.get('schema_version') != 1:
        raise ValueError('Expected a mapping with schema_version: 1')
    if cfg.get('engine_revision') != 'R4':
        raise ValueError('Workbench only supports Revision 4 engine')
    profiles = cfg.get('profiles')
    scenarios = cfg.get('scenarios')
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError('profiles must be a nonempty mapping')
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError('scenarios must be a nonempty mapping')
    for key in profiles:
        resolve_reference(cfg, key)
        workload_scaling(cfg, key)
        locomotion_reference(cfg,key)
    for scenario_key, scenario in scenarios.items():
        if not isinstance(scenario, dict) or not isinstance(scenario.get('actors'), dict) or not scenario['actors']:
            raise ValueError(f'{scenario_key}: actors must be nonempty')
        objective=scenario.get('objective')
        if 'grapple_encounter' in scenario: validate_grapple(scenario)
        if 'grapple_encounter' in scenario and ('combat' in scenario or objective is not None):
            raise ValueError('resolved Grapple cannot be a scripted combat or equine scenario')
        if 'combat' in scenario and objective is not None:
            raise ValueError(f'{scenario_key}: combat and equine objectives are exclusive')
        if 'combat' in scenario: validate_case(scenario)
        if objective is not None:
            if not isinstance(objective,dict) or objective.get('kind')!='equine_160km':
                raise ValueError(f'{scenario_key}: unknown objective kind')
            number(objective.get('distance_km'),f'{scenario_key}: objective distance',100,200)
            number(objective.get('deadline_hours'),f'{scenario_key}: deadline',1,48)
            if not objective.get('joint_actors') or len(objective['joint_actors'])!=2:
                raise ValueError(f'{scenario_key}: joint_actors must list mount and rider')
            if any(x not in scenario['actors'] for x in objective['joint_actors']):
                raise ValueError(f'{scenario_key}: joint actor missing')
        if 'hard_schedule' in scenario and type(scenario['hard_schedule']) is not bool:
            raise ValueError(f'{scenario_key}: hard_schedule must be boolean')
        if scenario.get('hard_schedule') and scenario.get('assessment_kind') != 'fixed_duty':
            raise ValueError(f'{scenario_key}: hard_schedule requires fixed_duty assessment')
        period = scenario.get('daily_schedule_seconds')
        if period is not None: number(period, f'{scenario_key}: daily schedule length',1,86400*30)
        for label, actor in scenario['actors'].items():
            if not isinstance(actor, dict): raise ValueError(f'{label}: actor must be a mapping')
            if actor.get('profile') not in profiles: raise ValueError(f'{label}: unknown profile')
            fitness = number(actor.get('fitness',12), f'{label}: fitness', 1, 100)
            abilities=actor.get('abilities',{})
            if not isinstance(abilities,dict): raise ValueError(f'{label}: abilities must be a mapping')
            for key,value in abilities.items():
                if key not in ABILITIES: raise ValueError(f'{label}: unknown ability {key}')
                number(value, f'{label}: {key}',1,100)
            if 'constitution' in abilities and fitness > abilities['constitution']:
                raise ValueError(f'{label}: Fitness cannot exceed Constitution')
            number(actor.get('run_level',0), f'{label}: run_level', 0, 20)
            reps = actor.get('repeat',1)
            if type(reps) is not int or not 1 <= reps <= MAX_REPEATS:
                raise ValueError(f'{label}: repeat must be an integer 1..{MAX_REPEATS}')
            if 'combat' in scenario or 'grapple_encounter' in scenario:
                continue  # Encounter scripts use action programs; already validated above.
            segments = actor.get('segments')
            if not isinstance(segments, list) or not segments or len(segments)>MAX_SEGMENTS:
                raise ValueError(f'{label}: invalid segments')
            duration = 0
            for seg in segments:
                if not isinstance(seg, dict): raise ValueError(f'{label}: segment must be a mapping')
                duration += segment_duration(seg)
                demand=number(seg.get('demand',0), f'{label}: demand', 0,1)
                if seg.get('demand_basis','individual') not in ('individual','reference_fitness'):
                    raise ValueError(f'{label}: unrecognized demand_basis')
                if 'distance_km' in seg and 'pace_effort' not in seg:
                    raise ValueError(f'{label}: distance segment must specify pace_effort true or false')
                if seg.get('pace_effort') and 'distance_km' not in seg:
                    raise ValueError(f'{label}: pace_effort only valid on distance segments')
                actual_demand = physical_demand(cfg,actor,seg)
                number(actual_demand,f'{label}: effective demand',0,3)
                number(seg.get('wear',1), f'{label}: wear', 0,10)
                if seg.get('sleep',False) and demand:
                    raise ValueError(f'{label}: sleeping segment requires demand 0')
                number(seg.get('run_level',actor.get('run_level',0)),f'{label}: segment run level',0,20)
                execution=seg.get('execution','fixed_pace')
                if execution not in ('fixed_pace','fixed_work'):
                    raise ValueError(f'{label}: invalid execution mode {execution}')
                if scenario.get('hard_schedule') and execution != 'fixed_pace':
                    raise ValueError(f'{scenario_key}: hard schedule forbids reduced-pace fixed_work; this is a non-negotiable duty')
                if execution=='fixed_work':
                    if objective is not None: raise ValueError(f'{scenario_key}: equine objective requires fixed pace for all phases')
                    if seg.get('sleep') or seg.get('all_out') or actual_demand<=0:
                        raise ValueError(f'{label}: fixed_work must be nonzero work, not sleep/all-out')
                    number(seg.get('reserve_floor',0.25),f'{label}: reserve_floor',0,0.95)
                    number(seg.get('pacing_window_seconds',600),f'{label}: pacing_window_seconds',30,86400)
                    number(seg.get('maximum_duration_factor',3),f'{label}: maximum_duration_factor',1,100)
            if objective is not None:
                if any(seg.get('execution','fixed_pace')!='fixed_pace' for seg in segments):
                    raise ValueError(f'{scenario_key}: equine objective requires fixed pace, no work extension')
                # Joint objective enforces the SAME pace, distance and hold schedule
                # rather than allowing either Being to silently alter the assignment.
                if reps != 1: raise ValueError(f'{scenario_key}: objective actors cannot repeat')
                ride=[seg for seg in segments if 'distance_km' in seg]
                if len(ride)!=6 or abs(sum(seg['distance_km'] for seg in ride)-objective['distance_km'])>1e-5:
                    raise ValueError(f'{scenario_key}: require six phases totaling objective distance')
                if any(not 20<=seg['distance_km']<=40 for seg in ride):
                    raise ValueError(f'{scenario_key}: phase distances must be 20–40 km')
                if len(segments)!=11 or any('distance_km' in segments[i] for i in (1,3,5,7,9)):
                    raise ValueError(f'{scenario_key}: exactly five holds between six riding phases required')
                holds=[segments[i]['seconds'] for i in (1,3,5,7,9)]
                if any(hold<30*60 or hold>60*60 for hold in holds) or not any(hold>=50*60 for hold in holds):
                    raise ValueError(f'{scenario_key}: five 30–60 minute holds, one >=50 minutes required')
                if any(segments[i]['seconds'] < (max(30,segments[i-1]['distance_km']))*60 for i in (1,3,5,7,9)):
                    raise ValueError(f'{scenario_key}: hold shorter than preceding phase minimum')
            if period is not None and abs(duration-float(period))>0.01:
                raise ValueError(f'{scenario_key}: schedule blocks must total {period} seconds per duty cycle, got {duration}')
            if duration * reps>MAX_SIM_SECONDS:
                raise ValueError(f'{label}: actor timeline longer than 30 days')
    for scenario_key,scenario in scenarios.items():
        objective=scenario.get('objective')
        if objective is None:continue
        one,two=(scenario['actors'][x]['segments'] for x in objective['joint_actors'])
        for a,b in zip(one,two):
            if abs(segment_duration(a)-segment_duration(b))>1e-5 or abs(a.get('distance_km',0)-b.get('distance_km',0))>1e-5 or a.get('speed_kmh')!=b.get('speed_kmh'):
                raise ValueError(f'{scenario_key}: mount and rider must share journey schedule')
    return cfg


def resolve_reference(cfg, name, seen=None):
    """Resolve inherited *reference* values, before optional Fitness/Run scaling."""
    seen = set() if seen is None else set(seen)
    if name in seen: raise ValueError(f'Profile inheritance cycle involving {name}')
    profiles = cfg['profiles']
    if name not in profiles: raise ValueError(f'Missing profile: {name}')
    spec = profiles[name]
    if not isinstance(spec, dict): raise ValueError(f'{name} profile must be a mapping')
    parent = spec.get('parent')
    inherited = resolve_reference(cfg,parent,seen|{name}) if parent else dict(DEFAULTS)
    values = spec.get('parameters',{})
    if not isinstance(values,dict): raise ValueError(f'{name}: parameters must be mapping')
    for key,val in values.items():
        if key not in DEFAULTS: raise ValueError(f'{name}: unknown parameter {key}')
        inherited[key]=number(val,f'{name}.{key}',*BOUNDS[key])
    scaling=spec.get('scaling','none')
    if scaling not in ('none','human_r4'): raise ValueError(f'{name}: unknown scaling mode {scaling}')
    if inherited['critical_fresh'] * inherited['critical_floor'] > inherited['peak_floor']:
        raise ValueError(f'{name}: critical_floor and peak_floor imply C > H at B=0')
    return inherited


def effective_profile(cfg, name, fitness=12, run_level=0, running=False):
    values=resolve_reference(cfg,name)
    mode=cfg['profiles'][name].get('scaling','none')
    if mode=='human_r4':
        # Use the authentic R4 Fitness/Run scaling *ratios* and apply them to the
        # inherited/tuned reference profile. This makes the workbench editable
        # without duplicating the physics; it is a documented adapter.
        default=human_profile(12)
        adjusted=human_profile(fitness,run_level=round(run_level),running=running)
        for field in ('critical_fresh','fast_budget','fast_recovery','slow_depletion',
                      'slow_recovery_awake','slow_recovery_sleep'):
            values[field] *= getattr(adjusted,field)/getattr(default,field)
        values['critical_fresh']=min(.8,values['critical_fresh'])
    p=Profile(**values)
    if critical(0,p)>p.peak_floor:
        raise ValueError(f'{name}: scaled critical output exceeds peak at exhausted B')
    return p


def _snapshot(time_s,state,profile,segment='',demand=0,actual=0,capped=False):
    return {'seconds': round(time_s,5), 'q': round(state.q*100,5),
            'b': round(state.b*100,5), 'critical': round(critical(state.b,profile)*100,5),
            'max_output':round(peak(state.q,state.b,profile)*100,5),
            'segment':segment,'demand':round(demand*100,4),
            'actual':round(actual*100,4),'capped':bool(capped)}


def simulate_actor(cfg, actor):
    """Simulate segments, distinguishing prescribed pace from prescribed work.

    fixed_pace: old R4 semantics, halt if desired effort becomes infeasible.
    fixed_work: perform the entire prescribed amount of work, adapting the
    output smoothly as available sustainable output declines. Work/progress
    is derived per activity, not a third persistent fatigue state.
    """
    state=State();elapsed=0.;points=[];first_cap=None;first_fixed_cap=None;first_allout_cap=None
    repeats=actor.get('repeat',1)
    segs=actor['segments']
    planned_total=sum(segment_duration(x) for x in segs)*repeats
    sample_interval=max(.5,planned_total/450)
    total_segments=len(segs)*repeats
    if total_segments > 20000: raise ValueError('Too many repeated segments')
    last_profile=effective_profile(cfg,actor['profile'],actor.get('fitness',12),actor.get('run_level',0),actor.get('running',False))
    points.append(_snapshot(0,state,last_profile,'Start'))
    failed_segment=None; last_reference_demand=None; last_effective_demand=None
    work_target=0.0; work_completed=0.0; work_planned_s=0.0; work_actual_s=0.0
    extended_by_s=0.0; completed_segments=[]; last_plot_s=0.0; distance_reached=0.0; checkpoints=[]
    for _ in range(repeats):
        for seg in segs:
            duration=segment_duration(seg);desired=physical_demand(cfg,actor,seg);wear=seg.get('wear',1.0)
            last_reference_demand=seg.get('demand');last_effective_demand=desired
            mode=seg.get('execution','fixed_pace')
            name=seg.get('name','Activity')
            segment_start=elapsed
            profile=effective_profile(cfg,actor['profile'],actor.get('fitness',12),
                    seg.get('run_level',actor.get('run_level',0)),
                    seg.get('running',actor.get('running',False)))
            if mode=='fixed_work':
                # Total work is an actual requirement, unlike a prescribed pace.
                # The athlete can slow down; elapsed time then extends while
                # all other work and recovery values stay in the same model.
                required=desired*duration
                work_target+=required; work_planned_s+=duration
                completed_work=0.0; spent_s=0.0
                q_floor=float(seg.get('reserve_floor',.25))
                window=float(seg.get('pacing_window_seconds',600))
                limit=float(seg.get('maximum_duration_factor',3))*duration
                # A small integration interval makes the pace controller smooth
                # as critical output changes. Work is always integrated from
                # actually delivered output, never the prescribed nominal pace.
                while completed_work+1e-8 < required:
                    c=critical(state.b,profile)
                    # A controller can use fast reserve for short bursts, but
                    # approaches sustainable output before reserve exhaustion.
                    suggested=c+(state.q-q_floor)*profile.fast_budget/window
                    actual=min(desired,peak(state.q,state.b,profile),max(0.0,suggested))
                    if actual <= 1e-8:
                        failed_segment=name;break
                    dt=min(15.0,(required-completed_work)/actual,limit-spent_s)
                    if dt<=1e-7 or elapsed+dt>MAX_SIM_SECONDS:
                        failed_segment=name;break
                    r=evolve(state,actual,dt,profile,wear=wear,max_step=min(2.,dt))
                    state=r.state
                    delivered=actual*dt
                    completed_work+=delivered;work_completed+=delivered
                    spent_s+=dt;work_actual_s+=dt;elapsed+=dt
                    if elapsed-last_plot_s>=sample_interval:
                        points.append(_snapshot(elapsed,state,profile,name,desired,actual,False))
                        last_plot_s=elapsed
                extra=spent_s-duration
                extended_by_s+=extra
                completed_segments.append({'name':name,'execution':mode,
                  'target_seconds':round(duration,2),'actual_seconds':round(spent_s,2),
                  'completion_percent':round(min(100,100*completed_work/required),3),
                  'mean_pace_percent':round(100*duration/spent_s,2) if spent_s else 0})
                points.append(_snapshot(elapsed,state,profile,name,desired,
                    min(desired,critical(state.b,profile)),failed_segment is not None))
                last_plot_s=elapsed
                if failed_segment:
                    if first_cap is None:first_cap=round(elapsed,3)
                    if first_fixed_cap is None:first_fixed_cap=round(elapsed,3)
                    break
            else:
                n=max(1,ceil(duration/sample_interval))
                chunk=duration/n
                for _ in range(n):
                    before=elapsed
                    if desired>1 or (not seg.get('all_out',False) and desired>peak(state.q,state.b,profile)+1e-9):
                        failed_segment=name
                        if first_cap is None:first_cap=round(elapsed,3)
                        if first_fixed_cap is None:first_fixed_cap=round(elapsed,3)
                        break
                    result=evolve(state,min(desired,1),chunk,profile,wear=wear,
                                sleep=bool(seg.get('sleep',False)),max_step=min(2.,chunk))
                    if result.capped:
                        if first_cap is None:first_cap=round(before,3)
                        if seg.get('all_out',False):
                            if first_allout_cap is None:first_allout_cap=round(before,3)
                        else:
                            lo=0.;hi=chunk
                            for _ in range(22):
                                mid=(lo+hi)/2
                                if evolve(state,desired,mid,profile,wear=wear,
                                          sleep=bool(seg.get('sleep',False)),max_step=min(2.,mid)).capped:
                                    hi=mid
                                else:lo=mid
                            state=evolve(state,desired,lo,profile,wear=wear,
                                sleep=bool(seg.get('sleep',False)),max_step=min(2.,max(lo,.001))).state
                            elapsed=before+lo;failed_segment=name
                            first_fixed_cap=round(elapsed,3)
                            points.append(_snapshot(elapsed,state,profile,name,desired,desired,True))
                            break
                    state=result.state;elapsed+=chunk
                    points.append(_snapshot(elapsed,state,profile,name,desired,result.actual_u,result.capped))
                completed_segments.append({'name':name,'execution':mode,
                  'target_seconds':round(duration,2),'actual_seconds':round(elapsed-segment_start,2),
                  'completion_percent':round(100*min(1.0,max(0.0,(elapsed-segment_start)/duration)),2)})
            if 'distance_km' in seg:
                # A fixed speed is mandatory. Only actual elapsed riding counts.
                added=seg['distance_km']*max(0,elapsed-segment_start)/duration
                distance_reached+=added
                checkpoints.append({'phase':name,'km':round(distance_reached,3),
                    'elapsed_hours':round(elapsed/3600,4), 'q_percent':round(state.q*100,2),
                    'b_percent':round(state.b*100,2),'complete':failed_segment is None})
            last_profile=profile
            if failed_segment:break
        if failed_segment:break
    scaling=workload_scaling(cfg,actor['profile'])
    return {'points':points,'summary':{'q':round(state.q*100,2),'b':round(state.b*100,2),
            'critical':round(critical(state.b,last_profile)*100,2),
            'max_output':round(peak(state.q,state.b,last_profile)*100,2),
            'first_cap_interval_start_s':first_cap,
            'first_infeasible_interval_start_s':first_fixed_cap,
            'first_all_out_interval_start_s':first_allout_cap,
            'total_seconds':round(elapsed,2),'planned_seconds':round(planned_total,2),
            'completed':failed_segment is None,'failed_segment':failed_segment,
            'last_reference_demand':last_reference_demand,
            'last_effective_demand':last_effective_demand,
            'work_target':round(work_target,3),'work_completed':round(work_completed,3),
            'work_planned_seconds':round(work_planned_s,2),
            'work_actual_seconds':round(work_actual_s,2),
            'work_pace_percent':round(100*work_planned_s/work_actual_s,2) if work_actual_s else None,
            'schedule_delay_seconds':round(extended_by_s,2),
            'segment_results':completed_segments,'distance_km':round(distance_reached,3),
            'checkpoints':checkpoints},
            'effective_parameters':asdict(last_profile),'workload_scaling':scaling,
            'being':{'fitness':actor.get('fitness',12),'run_level':actor.get('run_level',0),
                     'abilities':actor.get('abilities',{}),'profile':actor['profile']}}

def clip_actor_to_elapsed(actor, elapsed_s):
    """Materialize physical activity up to an externally imposed joint stop.

    A course cannot continue after its mount or rider fails; no third reserve,
    ad-hoc recovery, or workload pacing is introduced.
    """
    from copy import deepcopy
    clipped=deepcopy(actor)
    clipped['repeat']=1
    out=[];remaining=elapsed_s
    for segment in actor['segments']:
        if remaining<=1e-6:break
        duration=segment_duration(segment)
        if remaining+1e-7 >= duration:
            out.append(deepcopy(segment));remaining-=duration
        else:
            part=deepcopy(segment)
            if 'distance_km' in part:part['distance_km']*=remaining/duration
            else:part['seconds']=remaining
            part['name']=part.get('name','Activity')+' (joint stop)'
            out.append(part)
            remaining=0
    clipped['segments']=out
    return clipped


def simulate(cfg, scenario_name):
    validated_config(cfg)
    if scenario_name not in cfg['scenarios']: raise ValueError('Unknown scenario')
    scen=cfg['scenarios'][scenario_name]
    if 'grapple_encounter' in scen:
        result=simulate_encounter(cfg,scen,effective_profile,workload_scaling)
        result['scenario']=scenario_name
        return result
    if 'combat' in scen:
        result=simulate_combat(cfg,scen,effective_profile,workload_scaling)
        result['scenario']=scenario_name
        return result
    outputs={name:simulate_actor(cfg,actor) for name,actor in scen['actors'].items()}
    objective_result=None
    if scen.get('objective'):
        rule=scen['objective'];actors=rule['joint_actors'];result=[outputs[name]['summary'] for name in actors]
        all_finished=all(x['completed'] for x in result)
        earliest_failure=min((x for x in result if not x['completed']),key=lambda x:x['total_seconds'],default=None)
        elapsed=max(x['total_seconds'] for x in result) if all_finished else earliest_failure['total_seconds']
        if earliest_failure is not None:
            # The other Being cannot continue after this joint ride has stopped.
            for name in actors:
                if outputs[name]['summary']['total_seconds']>elapsed+1e-5:
                    outputs[name]=simulate_actor(cfg,clip_actor_to_elapsed(scen['actors'][name],elapsed))
                    outputs[name]['summary']['interrupted_by_joint_failure']=True
        actual_distance=min(outputs[name]['summary']['distance_km'] for name in actors)
        reason=('fatigue requirements sustained; veterinary clearance not assessed' if all_finished and elapsed <= rule['deadline_hours']*3600
                else 'deadline exceeded' if all_finished else f"required pace became infeasible during {earliest_failure['failed_segment']}")
        objective_result={'kind':rule['kind'],'distance_km':rule['distance_km'],
            'distance_reached_km':round(actual_distance,3),
            'deadline_hours':rule['deadline_hours'],'elapsed_hours':round(elapsed/3600,3),
            'mount_and_rider_feasible':all_finished and elapsed <= rule['deadline_hours']*3600,'reason':reason,
            'vet_clearance':'not modeled; cannot claim official competition completion',
            'joint_actors':actors}
    return {'scenario':scenario_name, 'title':scen.get('title',scenario_name),
            'description':scen.get('description',''),
            'assessment_kind':scen.get('assessment_kind','uncalibrated'),
            'assessment_note':scen.get('assessment_note','No external success criteria verified.'),
            'objective':objective_result,'actors':outputs}


BUILD_ID = "R4.9 · UNIVERSAL FATIGUE"

class APIHandler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(STATIC),**kwargs)

    def send_json(self,obj,status=200):
        encoded=json.dumps(obj,allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(encoded)))
        self.end_headers();self.wfile.write(encoded)

    def end_headers(self):
        # Deliberately disable caching of local application assets. The previous
        # release reused these URLs and could display an older UI after upgrade.
        if not hasattr(self, '_json_cache_headers'):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
        super().end_headers()

    def do_GET(self):
        if self.path=='/api/build':
            self.send_json({'build':BUILD_ID, 'root':str(ROOT)})
        elif self.path=='/api/default':
            with CONFIG_PATH.open(encoding='utf-8') as f: cfg=yaml.safe_load(f)
            self.send_json({'build':BUILD_ID,'config':cfg,'yaml':CONFIG_PATH.read_text(encoding='utf-8'),'schema':SCHEMA})
        else:
            super().do_GET()

    def do_POST(self):
        try:
            size=int(self.headers.get('Content-Length',0))
            if size<=0 or size>524288: raise ValueError('Request exceeds 512 KB limit or is empty')
            request=json.loads(self.rfile.read(size))
            if self.path=='/api/parse':
                cfg=yaml.safe_load(request['yaml'])
                validated_config(cfg)
                self.send_json({'config':cfg})
            elif self.path=='/api/export':
                cfg=validated_config(request['config'])
                self.send_json({'yaml':yaml.safe_dump(cfg,sort_keys=False,allow_unicode=True,width=100)})
            elif self.path=='/api/manual-card':
                cfg=validated_config(request['config']); name=request['scenario']; actor=request['actor']
                from manual_cards import make_card
                self.send_json({'markdown':make_card(cfg,name,actor)})
            elif self.path=='/api/simulate':
                cfg=request['config'];name=request['scenario']
                self.send_json(simulate(cfg,name))
            else:self.send_json({'error':'Unknown endpoint'},404)
        except (ValueError,KeyError,TypeError,yaml.YAMLError) as e:
            self.send_json({'error':str(e)},400)
        except Exception:
            traceback.print_exc()
            self.send_json({'error':'Unexpected server error; see terminal output'},500)


def main():
    parser=argparse.ArgumentParser(description='Universe fatigue configuration workbench')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    cfg=yaml.safe_load(CONFIG_PATH.read_text())
    validated_config(cfg)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),APIHandler)
    print(f'Universe Fatigue Workbench {BUILD_ID}: http://127.0.0.1:{args.port}',flush=True)
    print(f'Application directory: {ROOT}',flush=True)
    print('Local-only server. Press Ctrl+C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
