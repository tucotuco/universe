"""Universe Encounters physical fatigue: two-reserve R4 candidate.

This is a sandbox reference/calibration model, NOT an empirical physiology model.
Only Q (fast reserve) and B (long reserve) are persistent fatigue state.
Inputs: workload u relative to individual's fresh maximal output, an activity wear multiplier,
physiological parameters, and time. This implementation resolves workload in finite timesteps;
fixed-work closed-form state updates are implemented where B coupling is frozen over a step.
"""
from dataclasses import dataclass, replace
from math import exp, sqrt

@dataclass(frozen=True)
class State:
    q: float = 1.0   # 0 empty, 1 fully available
    b: float = 1.0

@dataclass(frozen=True)
class Profile:
    critical_fresh: float = .60  # sustainably available output at B=1 (as fraction peak)
    critical_floor: float = .25  # fraction of critical output when B fully depleted
    peak_floor: float = .55      # fresh-peak output remaining when B fully depleted
    peak_curve: float = 2.0     # Q-to-peak output response
    fast_budget: float = 20.0   # seconds of peak-normalized work available above critical
    fast_recovery: float = 60.0 # seconds to replenish Q at complete rest
    slow_depletion: float = 7200.0 # s, slow depletion timescale at high actual exertion
    slow_recovery_awake: float = 86400.0 # s for passive recovery of B
    slow_recovery_sleep: float = 43200.0
    slow_baseline: float = .10 # no accumulation below this workload

def human_profile(fitness: float, *, run_level: int = 0, running: bool = False) -> Profile:
    """Provisional human defaults. Run specialization applies only while actually running.

    Fitness is a trainable ability (not a skill), and remains unchanged by fatigue.
    6..20 below are convenient example values, NOT an imposed universal score range.
    """
    if fitness <= 0 or not 0 <= run_level <= 20:
        raise ValueError("Invalid Fitness or Run level")
    r=run_level if running else 0
    skill=1+0.01*r
    return replace(Profile(),
        critical_fresh=min(.80,.60*(1+.006*(fitness-12)+.0015*r)),
        fast_budget=20*sqrt(fitness/12)*skill,
        fast_recovery=60*sqrt(12/fitness),
        slow_depletion=7200*(fitness/12)*skill,
        slow_recovery_awake=86400*(12/fitness),
        slow_recovery_sleep=43200*(12/fitness))

@dataclass(frozen=True)
class Step:
    state: State
    actual_u: float
    capped: bool


def critical(b, p=Profile()):
    return p.critical_fresh * (p.critical_floor + (1-p.critical_floor) * b)

def peak(q, b, p=Profile()):
    c = critical(b,p)
    maximum = 1 - (1-p.peak_floor)*(1-b)
    assert maximum >= c
    return c + (maximum-c) * (1-(1-q)**p.peak_curve)

def slow_exertion(u, p=Profile(), wear=1.0):
    return wear * max(0.0,(u-p.slow_baseline)/(1-p.slow_baseline))**2

def evolve(s, u_req, seconds, p=Profile(), wear=1., sleep=False, max_step=2.0):
    """Sample-and-hold actual work/peak across small substeps.
    An infeasible request is capped; returns whether request was ever infeasible.
    """
    if not 0 <= u_req <= 1 or seconds<0 or wear<0:
        raise ValueError("bad workload/time/wear")
    if sleep and u_req != 0:
        raise ValueError('sleeping requires u=0')
    n = max(1,round(seconds/max_step + 0.499999999))
    dt=seconds/n
    q,b=s.q,s.b
    was_capped = False
    actual_u=0
    for _ in range(n):
        cap=peak(q,b,p)
        u=min(u_req,cap)
        was_capped |= u_req > cap+1e-9
        c=critical(b,p)
        # exact local Q integral at held b and effort u; finite above-critical expenditure
        if u>c:
            q = max(0.0, q - (u-c)*dt/p.fast_budget)
        else:
            q = 1-(1-q)*exp(-dt*(c-u)/(max(c,1e-9)*p.fast_recovery))
        # B depletion and recovery act simultaneously. Frozen c,u during substep.
        depletion=slow_exertion(u,p,wear)/p.slow_depletion
        tb=p.slow_recovery_sleep if sleep else p.slow_recovery_awake
        recharge=max(0,(c-u)/max(c,1e-9))/tb
        k=depletion+recharge
        if k:
            beq = recharge/k
            b = beq+(b-beq)*exp(-k*dt)
        q=max(0.0,min(1.,q));b=max(0.0,min(1.,b))
        actual_u=u
    return Step(State(q,b),actual_u,was_capped)

def finish_time(u, duration, p=Profile(), wear=1, step=30., start=State()):
    s=start; t=0.0
    while t < duration-1e-6:
        dt=min(step,duration-t)
        output=evolve(s,u,dt,p,wear,max_step=min(step,10))
        if output.capped:
            return t,output.state
        s=output.state
        t+=dt
    return duration,s

def max_steady_effort(duration,p=Profile(),wear=1.,step=30.):
    lo,hi=0.,1.
    for _ in range(30):
        mid=(lo+hi)/2
        t,_=finish_time(mid,duration,p,wear,step)
        if t>=duration-1e-6:lo=mid
        else:hi=mid
    t,s=finish_time(lo,duration,p,wear,step)
    return lo,s

def report(label,s,p=Profile(),u=None):
    print(f'{label:39s} Q={s.q*100:6.1f}% B={s.b*100:6.1f}% critical={critical(s.b,p):.3f} peak={peak(s.q,s.b,p):.3f}' + (f'  u={u:.3f}' if u is not None else ''))

def cases():
    p=Profile()
    print('Single bouts:')
    for dur in (10,45,60):
        r=evolve(State(),1,dur,p,max_step=.2)
        report(f'maximal effort {dur}s (cap={r.capped})',r.state)
    print('\nMaximum sustainable constant effort given a duration (not speed, race time or direct empirical calibration):')
    for name,hours,wear in [('Ironman-duration',10.5,1.0),('Ultra-duration',24,1.3),('Marathon-duration',2.5,1.3),('400m-like effort',.0125,1)]:
        u,s=max_steady_effort(hours*3600,p,wear)
        report(f'{name}, {hours:g} h',s,u=u)
    print('\nRoman marching:')
    s=State()
    for d in range(1,5):
        s=evolve(s,.27,5*3600,p,wear=1.1,max_step=60).state
        report(f'Day {d} after march',s)
        s=evolve(s,.40,2*3600,p,wear=1.0,max_step=60).state
        report(f'Day {d} after campwork',s)
        s=evolve(s,.10,9*3600,p,max_step=60).state
        s=evolve(s,0,8*3600,p,sleep=True,max_step=60).state
        report(f'Day {d} after rest/sleep',s)
    print('\nMount example (no equine calibration is implied)')
    horse=Profile(critical_fresh=.66,fast_budget=25,slow_depletion=14400,slow_recovery_awake=144000)
    rider=Profile()
    report('Horse relay leg 72min @u=.37',evolve(State(),.37,72*60,horse,max_step=30).state,horse)
    report('Rider 9 h @u=.20',evolve(State(),.20,9*3600,rider,max_step=30).state)
    print('\nCombat:')
    for pattern in [('moderate',(1,.85,2,.20)),('severe',(2,.98,1,.35)),('active grapple',(3,.86,1,.20))]:
        name,(n1,u1,n2,u2)=pattern
        s=State();capped=False
        for cyc in range(100):
            for n,u in ((n1,u1),(n2,u2)):
                z=evolve(s,u,n,p,max_step=.5)
                capped|=z.capped
                s=z.state
            if (cyc+1)*(n1+n2) in (60,300):report(name+f' {(cyc+1)*(n1+n2)}s capped={capped}',s)
            if (cyc+1)*(n1+n2)>=300:break
        report(name+f' last={ (cyc+1)*(n1+n2)}s capped={capped}',s)

def invariants():
    p=Profile();s=State(.4,.6)
    a=evolve(s,.35,3600,p,max_step=1.).state
    b=evolve(s,.35,1800,p,max_step=1.).state
    b=evolve(b,.35,1800,p,max_step=1.).state
    assert abs(a.q-b.q)<1e-9 and abs(a.b-b.b)<1e-9
    for initial in (State(),State(0,0),State(.1,.2)):
        for u in (0,.1,.45,1):
            r=evolve(initial,u,60,p,max_step=.5)
            assert 0<=r.state.q<=1 and 0<=r.state.b<=1
            assert 0<=peak(r.state.q,r.state.b,p)<=1
    s=evolve(State(.1,.2),0,3600).state
    assert s.q>.1 and s.b>.2
    assert peak(0,1,p)==critical(1,p)
    assert human_profile(18,run_level=20,running=True).fast_budget>human_profile(12).fast_budget
    print('Invariants passed.')

if __name__=='__main__':
    invariants()
    cases()
    print('\nAbility-scaled endurance race benchmarks (elite human Fitness18 Run20):')
    pp=human_profile(18,run_level=20,running=True)
    for name,hours,wear in [('Marathon-like',2.5,1.3),('Ironman-duration with sustained running specialization',10.5,1),('Ultra-duration',24,1.3)]:
        u,st=max_steady_effort(hours*3600,pp,wear)
        report(name,st,pp,u)

# Distances and workload curves below are illustrative mode reference profiles,
# not universal human athletic norms or empirical calibration.
def human_fresh_sprint_speed(fitness: float, run_level: int = 0) -> float:
    return .4572*fitness + .19652*run_level*fitness/18

def speed_from_effort(u: float, *, critical_fraction: float, critical_speed: float,
                      maximum_speed: float) -> float:
    if not 0 <= u <= 1 or not 0 < critical_fraction < 1 or not 0 < critical_speed < maximum_speed:
        raise ValueError('Invalid locomotion/work profile')
    if u <= critical_fraction:
        return critical_speed*(u/critical_fraction)
    return critical_speed+(maximum_speed-critical_speed)*(u-critical_fraction)/(1-critical_fraction)

def effort_from_speed(speed: float, *, critical_fraction: float, critical_speed: float,
                      maximum_speed: float) -> float:
    if not 0 <= speed <= maximum_speed or not 0 < critical_fraction < 1 or not 0 < critical_speed < maximum_speed:
        raise ValueError('Invalid locomotion/work profile')
    if speed <= critical_speed:
        return critical_fraction*speed/critical_speed
    return critical_fraction+(1-critical_fraction)*(speed-critical_speed)/(maximum_speed-critical_speed)


def triathlon_example(scale: float, display=False):
    """One 3.8km/180km/42.195km staged event at chosen effort strategy.
    Distances and base speeds are illustrative. There is no prescribed exhaustion at finish.
    """
    f=18
    base=human_profile(f)
    run=human_profile(f,run_level=20,running=True)
    phases=[('Swim',3800,1.65,2.6,.88,base,.90),
            ('Bike',180000,13,22,.94,base,.75),
            ('Run',42195,5.3,human_fresh_sprint_speed(18,20),1,run,1.25)]
    st=State();total=0;records=[];any_cap=False
    for name,d,vcrit,vmax,factor,p,wear in phases:
        u=scale*factor
        v=speed_from_effort(u,critical_fraction=p.critical_fresh,critical_speed=vcrit,maximum_speed=vmax)
        dt=d/v
        r=evolve(st,u,dt,p,wear=wear,max_step=10)
        any_cap|=r.capped
        st=r.state;total+=dt
        records.append((name,dt,v,u,st,r.capped))
        if name!='Run':
            st=evolve(st,.10,300,base,max_step=10).state
            total+=300
    if display:
        for name,dt,v,u,st,capped in records:
            print(f'{name:6} time={dt/60:6.1f} min speed={v:5.2f} m/s u={u:.3f} Q={st.q*100:5.1f}% B={st.b*100:5.1f}% capped={capped}')
        print(f'Race time={total/3600:.3f} hours, any demand exceeded capability={any_cap}')
    return any_cap,total,st,records

def triathlon_steady_strategy():
    lo,hi=.10,1.
    for _ in range(28):
        m=(lo+hi)/2
        capped,_,_,_=triathlon_example(m)
        if capped:hi=m
        else:lo=m
    return lo


def extra_tests():
    # Profile-mapping invertibility and consistency under refinement.
    pf=human_profile(18,run_level=20,running=True)
    v=7.1
    args={'critical_fraction':pf.critical_fresh,'critical_speed':5.3,'maximum_speed':human_fresh_sprint_speed(18,20)}
    u=effort_from_speed(v,**args)
    assert abs(speed_from_effort(u,**args)-v)<1e-9
    for d in (.2,1.2,5,30):
        a=evolve(State(.5,.8),.61,600,pf,wear=1.3,max_step=d).state
        b=evolve(State(.5,.8),.61,600,pf,wear=1.3,max_step=.2).state
        assert abs(a.q-b.q)<.003 and abs(a.b-b.b)<.003
    print('Additional tests passed (effort-speed inversion, resolution stability).')

if __name__=='__main__':
    extra_tests()
    print('\nDistance-based full-distance triathlon:')
    base=triathlon_steady_strategy()
    print(f'Highest approximately feasible proportional pacing scale: {base:.5f}')
    for factor in (.95,1,1.02):
        print(f'\nRelative pacing scale {factor:.2f}x')
        triathlon_example(base*factor,display=True)
