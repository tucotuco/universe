'use strict';
const $ = id => document.getElementById(id);
const clone = x => JSON.parse(JSON.stringify(x));
let baseline = null, working = null, selectedProfile = '', selectedScenario = '', selectedActor = '';
let candidateResults = null, baselineResults = null, rerunTimer = null, requestSequence = 0;
let paramSpec = [], defaultParameters = {}, workloadSpec = {};
const pct = n => `${Number(n).toFixed(1)}%`;
const fmt = (n,d=3) => Number(n).toLocaleString('en-US',{maximumFractionDigits:d});
const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, body=null){
  const args = body===null ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
  const r=await fetch(path,args);
  const j=await r.json();
  if(!r.ok)throw Error(j.error || `HTTP ${r.status}`);
  return j;
}
function status(txt,err=false){$('run-status').textContent=txt;document.querySelector('.status-dot').style.background=err?'#e76b5b':'#16a34a';$('error').hidden=!err;if(err)$('error').textContent=txt;}
function profileParents(cfg,name){
  const names=[];let node=name;
  while(node){if(names.includes(node))break;names.push(node);node=cfg.profiles[node]?.parent;}
  return names.reverse();
}
function resolvedParams(cfg,name){
  const values={...defaultParameters};
  for(const node of profileParents(cfg,name))Object.assign(values,cfg.profiles[node].parameters||{});
  return values;
}
function updateSelections(){
  const oldProfile=selectedProfile;
  $('profile').innerHTML=Object.keys(working.profiles).map(k=>`<option value="${esc(k)}">${esc(k.replaceAll('_',' '))}</option>`).join('');
  selectedProfile=working.profiles[oldProfile]?oldProfile:(working.profiles.human?'human':Object.keys(working.profiles)[0]);
  $('profile').value=selectedProfile;
  const oldScenario=selectedScenario;
  $('scenario').innerHTML=Object.entries(working.scenarios).map(([k,v])=>`<option value="${esc(k)}">${esc(v.title||k)}</option>`).join('');
  selectedScenario=working.scenarios[oldScenario]?oldScenario:Object.keys(working.scenarios)[0];
  $('scenario').value=selectedScenario;
  updateActorSelection();
  if(!oldProfile)selectedProfile=working.scenarios[selectedScenario].actors[selectedActor].profile;
  $('profile').value=selectedProfile;
  renderParams();
  renderWorkloadParams();
}
function updateActorSelection(){
  const actors=working.scenarios[selectedScenario].actors;
  $('actor').innerHTML=Object.keys(actors).map(k=>`<option value="${esc(k)}">${esc(k)}</option>`).join('');
  selectedActor=actors[selectedActor]?selectedActor:Object.keys(actors)[0];
  $('actor').value=selectedActor;
  $('scenario-description').textContent=(working.scenarios[selectedScenario].description||'')+'\n\nASSESSMENT SCOPE: '+(working.scenarios[selectedScenario].assessment_note||'Unspecified; do not infer external task completion.');
  renderScenarioInputs();
}
function renderParams(){
  const obj=working.profiles[selectedProfile], effective=resolvedParams(working,selectedProfile);
  $('profile-meta').textContent=obj.scaling==='human_r4'?'Fitness scaling':'Reference physiology';
  $('profile-source').textContent='Inheritance: '+profileParents(working,selectedProfile).join(' → ');
  $('parameters').innerHTML=paramSpec.map(([key,label,min,max,step,explain,unit])=>{
    let v=effective[key];let own=Object.hasOwn(obj.parameters||{},key);
    return `<div class="param"><div class="param-top"><div><label for="num-${key}">${label}${unit==='seconds' ? ' (s)' : ''}</label> ${own?'<span class="edit-pill">override</span>':''}</div><input class="number-input" id="num-${key}" type="number" step="${step}" value="${v}"></div><div class="param-bottom"><span class="range-limit">${fmt(min,2)}</span><input class="range" id="rng-${key}" type="range" min="${min}" max="${max}" step="${step}" value="${Math.max(min,Math.min(max,v))}"><span class="range-limit">${fmt(max)}</span></div><div class="param-subtext">${explain}</div></div>`;
  }).join('');
  for(const [key,_label,min,max] of paramSpec){
    let number=$('num-'+key), range=$('rng-'+key);
    const change=(value,from)=>{
      const n=Number(value);if(!Number.isFinite(n))return;
      working.profiles[selectedProfile].parameters[key]=n;
      if(from==='number')range.value=Math.max(min,Math.min(max,n)); else number.value=n;
      schedule();renderDiff();
    };
    number.addEventListener('change',()=>change(number.value,'number'));
    range.addEventListener('input',()=>change(range.value,'range'));
  }
}
function resolvedWorkload(cfg,name){
  let ans={reference_fitness:12,fitness_exponent:0};
  for(const node of profileParents(cfg,name))Object.assign(ans,cfg.profiles[node].workload_scaling||{});
  return ans;
}
function resolvedLocomotion(cfg,name){
  let ans=null;
  for(const node of profileParents(cfg,name))if(cfg.profiles[node].locomotion)ans={...(ans||{}),...cfg.profiles[node].locomotion};
  return ans;
}
function renderWorkloadParams(){
  const obj=working.profiles[selectedProfile];
  const effective=resolvedWorkload(working,selectedProfile);
  $('workload-parameters').innerHTML=Object.entries(workloadSpec).map(([key,p])=>
    `<div class="repeat-row"><label for="work-${key}" title="${esc(p.description)}">${esc(p.label)}</label><input type="number" id="work-${key}" min="${p.min}" max="${p.max}" step="${p.step}" value="${effective[key]}"></div>`
  ).join('');
  const loc=resolvedLocomotion(working,selectedProfile);
  if(loc){
    const labels={reference_speed_kmh:'Reference riding speed (km/h)',reference_effort:'Relative output at reference speed',speed_exponent:'Speed–effort exponent',reference_fitness:'Locomotion reference Fitness',fitness_exponent:'Locomotion Fitness sensitivity'};
    $('workload-parameters').innerHTML+='<div class="eyebrow" style="margin-top:16px">LOCOMOTION CALIBRATION</div>'+
      Object.entries(loc).map(([key,value])=>`<div class="repeat-row"><label>${esc(labels[key]||key)}</label><input type="number" id="loc-${key}" step="0.01" value="${value}"></div>`).join('');
    for(const key of Object.keys(loc))$('loc-'+key).addEventListener('change',()=>{
      obj.locomotion??={};obj.locomotion[key]=Number($('loc-'+key).value);
      renderDiff();schedule();
    });
  }
  for(const key of Object.keys(workloadSpec)){
    $('work-'+key).addEventListener('change',()=>{
      obj.workload_scaling ??={};
      obj.workload_scaling[key]=Number($('work-'+key).value);
      renderDiff();schedule();
    });
  }
}
function renderBeing(){
  if(!candidateResults)return;
  const actor=working.scenarios[selectedScenario].actors[selectedActor];
  const result=candidateResults.actors[selectedActor];
  if(!result)return;
  const ab=actor.abilities||{};
  $('being-title').textContent=selectedActor;
  $('being-physiology').textContent='Physiology: '+actor.profile.replaceAll('_',' ');
  const traits=[['FIT',actor.fitness??12],['STR',ab.strength],['DEX',ab.dexterity],['CON',ab.constitution],['INT',ab.intelligence],['WIS',ab.wisdom],['CHA',ab.charisma]];
  $('being-abilities').innerHTML=traits.map(([name,value])=>`<div class="being-ability ${name==='FIT'?'highlight':''}"><b>${value===undefined?'—':esc(value)}</b><span>${name}</span></div>`).join('');
  $('being-training').textContent='Run level '+(actor.run_level??0)+(actor.running?' · running':'');
  if(working.scenarios[selectedScenario].grapple_encounter){
    const g=working.scenarios[selectedScenario].grapple_encounter;
    const scale=resolvedWorkload(working,actor.profile);
    $('being-training').textContent=`Grapple ${actor.improved_grapple??0} · Escape Artist ${actor.escape_artist??0} · Run ${actor.run_level??0}`;
    $('being-workload').innerHTML=Object.entries(g.costs).map(([kind,spec])=>{
      const eff=spec.demand*(spec.demand_basis==='reference_fitness'?Math.pow(scale.reference_fitness/(actor.fitness??12),spec.fitness_exponent??scale.fitness_exponent):1);
      return `<div>${esc(kind)}: <b>${pct(eff*100)}</b> demand</div>`;
    }).join('');return;
  }
  if(working.scenarios[selectedScenario].combat){
    const phases=working.scenarios[selectedScenario].combat.phases;
    $('being-workload').innerHTML=phases.map(ph=>{
      const scale=resolvedWorkload(working,actor.profile);
      const physical=x=>x.demand*(x.demand_basis==='reference_fitness'?Math.pow(scale.reference_fitness/(actor.fitness??12),x.fitness_exponent??scale.fitness_exponent):1);
      const prep=(ph.initial?.[selectedActor]||[]).map(x=>`${esc(x.name||x.kind)} ${pct(physical(x)*100)}`).join(', ');
      const program=ph.programs[selectedActor].map(x=>`${esc(x.name||x.kind)} ${pct(physical(x)*100)}`).join(' · ');
      return `<div><b>${esc(ph.name)}</b> (${fmt(ph.seconds,0)}s)<div>${prep ? 'Setup: '+prep+' · ' : ''}${program}</div></div>`;
    }).join('');
    return;
  }
  const segments=actor.segments.filter(seg=>seg.demand_basis==='reference_fitness');
  const scale=resolvedWorkload(working,actor.profile);
  const distanceSegments=actor.segments.filter(seg=>seg.distance_km!==undefined);
  if(distanceSegments.length){
    const loc=resolvedLocomotion(working,actor.profile);
    $('being-workload').innerHTML=distanceSegments.map(seg=>{
      const effort=seg.pace_effort&&loc ? loc.reference_effort*Math.pow(seg.speed_kmh/loc.reference_speed_kmh,loc.speed_exponent)*Math.pow(loc.reference_fitness/(actor.fitness??12),loc.fitness_exponent):seg.demand;
      return `<div>${esc(seg.name)}: <b>${fmt(seg.speed_kmh,2)} km/h</b> · relative output <b>${pct(effort*100)}</b></div>`;
    }).join('');return;
  }
  if(!segments.length){$('being-workload').textContent='Individually normalized effort (existing scenarios).';return;}
  $('being-workload').innerHTML=`<div>Reference Fitness ${fmt(scale.reference_fitness,1)} · sensitivity ${fmt(scale.fitness_exponent,2)}</div>`+
    segments.map(seg=>{const actual=seg.demand*Math.pow(scale.reference_fitness/(actor.fitness??12),scale.fitness_exponent);return `<div>${esc(seg.name)}: <b>${pct(actual*100)}</b> output demand</div>`}).join('');
}
function wireBeingInputs(actor,isCombat){
  for(const [id,key] of [['actor-profile','profile'],['actor-fitness','fitness'],['actor-run','run_level'],...(isCombat?[]:[['actor-repeat','repeat']])]){
    $(id)?.addEventListener('change',()=>{
      actor[key]=key==='profile'?$(id).value:Number($(id).value);
      renderDiff();schedule();
    });
  }
  for(const key of ['strength','dexterity','constitution','intelligence','wisdom','charisma']){
    $('actor-ability-'+key)?.addEventListener('change',()=>{
      actor.abilities??={};const v=$('actor-ability-'+key).value;
      if(v==='')delete actor.abilities[key];else actor.abilities[key]=Number(v);
      renderDiff();schedule();
    });
  }
}

function renderScenarioInputs(){
  const manual=$('manual-card-button');
  const supports=!!working.scenarios[selectedScenario].grapple_encounter;
  manual.disabled=!supports;
  manual.title=supports?'Generate card from this Being and the actual configured Grapple action demands':'Manual action cards are currently calibrated for Combat D only';
  const actor=working.scenarios[selectedScenario].actors[selectedActor];
  const actorOpts=Object.keys(working.profiles).map(k=>`<option value="${esc(k)}" ${actor.profile===k?'selected':''}>${esc(k)}</option>`).join('');
  let html=`<div class="repeat-row"><label>Physiology</label><select id="actor-profile" style="max-width:158px;border:1px solid #dce3ec;border-radius:5px;padding:6px">${actorOpts}</select></div><div class="repeat-row"><label>Fitness</label><input id="actor-fitness" type="number" min="1" max="100" step=".5" value="${actor.fitness??12}"></div><div class="repeat-row"><label>Run skill</label><input id="actor-run" type="number" min="0" max="20" step="1" value="${actor.run_level??0}"></div>${(working.scenarios[selectedScenario].combat||working.scenarios[selectedScenario].grapple_encounter)?'':`<div class="repeat-row"><label>Repeat whole sequence</label><input id="actor-repeat" type="number" min="1" max="2000" step="1" value="${actor.repeat??1}"></div>`}`;
  html+='<p class="sidebar-note">Other abilities (optional, displayed beside the graph; Constitution bounds Fitness).</p>';
  for(const [key,label] of [['strength','Strength'],['dexterity','Dexterity'],['constitution','Constitution'],['intelligence','Intelligence'],['wisdom','Wisdom'],['charisma','Charisma']]){
    html+=`<div class="repeat-row"><label for="actor-ability-${key}">${label}</label><input id="actor-ability-${key}" type="number" min="1" max="100" step="1" placeholder="—" value="${actor.abilities?.[key]??''}"></div>`;
  }
  const live=working.scenarios[selectedScenario].grapple_encounter;
  if(live){
    html+='<p class="small-help">Encounters R60 subset: opposed d20 Touch, opposed 3d6 Grab and Grapple, Escape and Break hold. No injuries, movement or pins. Only Q and B are fatigue reserves.</p>';
    for(const [key,desc] of [['improved_grapple','Improved Grapple'],['escape_artist','Escape Artist'],['attack_level','Touch attack level'],['defense_level','Touch defense level'],['armor_check_penalty','Armor check penalty']]){
      html+=`<div class="repeat-row"><label>${desc}</label><input type="number" min="0" max="30" step="1" value="${actor[key]??0}" data-gskill="${key}"></div>`;
    }
    html+=`<div class="repeat-row"><label>Physical check fatigue modifier</label><input id="grapple-fatigue-enabled" type="checkbox" ${live.fatigue_contest_penalty_enabled?'checked':''}><span>All physical checks/contests; no separate technique rule</span></div>`;
    html+='<p class="small-help">Universal Q/B physical-check table · fixed sensitivity 5. This is a rules constant, not a configurable Being or scenario parameter. The checkbox above is retained only for experimental before/after comparison.</p>';
    html+=`<div class="repeat-row"><label>Random seed</label><input id="grapple-seed" type="number" min="0" max="2147483647" step="1" value="${live.seed}"></div>`;
    html+='<div class="eyebrow">Action workload (shared physical demands)</div>';
    for(const [kind,cost] of Object.entries(live.costs)){
      html+=`<div class="combat-action-row"><label>${esc(kind)}</label><input data-gcost="${kind}" data-gkey="demand" type="number" min="0" max="1" step="0.01" value="${cost.demand}"><span>${cost.demand_basis==='reference_fitness'?'ref FIT':'self'}</span><input data-gcost="${kind}" data-gkey="wear" type="number" min="0" max="10" step=".05" value="${cost.wear}"><input data-gcost="${kind}" data-gkey="fitness_exponent" type="number" min="0" max="3" step=".05" value="${cost.fitness_exponent??0}"></div>`;
    }
    $('segments').innerHTML=html;
    wireBeingInputs(actor,true);
    $('grapple-fatigue-enabled').addEventListener('change',e=>{live.fatigue_contest_penalty_enabled=e.target.checked;renderDiff();schedule();});
    $('grapple-seed').addEventListener('change',e=>{live.seed=Number(e.target.value);renderDiff();schedule();});
    $('segments').querySelectorAll('[data-gskill]').forEach(i=>i.addEventListener('change',()=>{actor[i.dataset.gskill]=Number(i.value);renderDiff();schedule();}));
    $('segments').querySelectorAll('[data-gcost]').forEach(i=>i.addEventListener('change',()=>{live.costs[i.dataset.gcost][i.dataset.gkey]=Number(i.value);renderDiff();schedule();}));
    return;
  }
  const combat=working.scenarios[selectedScenario].combat;
  if(combat){
    html+='<p class="small-help">Prescribed Encounters action preparation times are fixed for each named action. The normalized effort, Fitness sensitivity and wear values are experimental calibration settings. No attack rolls, injuries, or grapple contest outcomes are simulated.</p>';
    combat.phases.forEach((ph,i)=>{
      html+=`<div class="combat-phase"><strong>${esc(ph.name)}</strong> <span>${ph.seconds}s</span></div>`;
      const actions=[...(ph.initial?.[selectedActor]||[]).map((v,j)=>[v,j,true]),...ph.programs[selectedActor].map((v,j)=>[v,j,false])];
      for(const [v,j,initial] of actions){
        html+=`<div class="combat-action-row"><label>${initial?'Setup · ':''}${esc(v.name||v.kind)} <small>(${esc(v.kind)})</small></label><input type="number" min="0" max="1" step="0.01" value="${v.demand}" data-cphase="${i}" data-caction="${j}" data-cinit="${initial?1:0}" data-ckey="demand" title="Required normalized output"><span>${v.demand_basis==='reference_fitness'?'ref FIT':'self'}</span><input type="number" min="0" max="10" step="0.05" value="${v.wear??1}" data-cphase="${i}" data-caction="${j}" data-cinit="${initial?1:0}" data-ckey="wear" title="Slow-wear coefficient"><input type="number" min="0" max="3" step="0.05" value="${v.fitness_exponent??resolvedWorkload(working,actor.profile).fitness_exponent}" data-cphase="${i}" data-caction="${j}" data-cinit="${initial?1:0}" data-ckey="fitness_exponent" title="Fixed-task Fitness sensitivity"></div>`;
      }
    });
    $('segments').innerHTML=html;
    wireBeingInputs(actor,true);
    $('segments').querySelectorAll('[data-cphase]').forEach(input=>input.addEventListener('change',()=>{
      const ph=combat.phases[Number(input.dataset.cphase)],list=input.dataset.cinit==='1'?ph.initial[selectedActor]:ph.programs[selectedActor];
      list[Number(input.dataset.caction)][input.dataset.ckey]=Number(input.value);
      renderDiff();schedule();
    }));
    return;
  }
  const distanceMode=!!working.scenarios[selectedScenario].objective;
  if(distanceMode)html+='<p class="small-help">Distance phases set required km and km/h; time follows from distance ÷ speed. A horse and rider must have exactly the same schedule. Change speed in both actors or edit both in exported YAML.</p>';
  html+='<table class="segments-table"><thead><tr><th>Segment</th><th>'+(distanceMode?'Distance / Hold':'Seconds')+'</th><th>'+(distanceMode?'Speed / Demand':'Demand')+'</th><th>Mode</th><th>Basis</th><th>Wear</th></tr></thead><tbody>';
  for(let i=0;i<actor.segments.length;i++){
    const v=actor.segments[i];
    const duration=v.distance_km!==undefined ? `<input data-seg="${i}" data-key="distance_km" type="number" min="20" max="40" step="1" value="${v.distance_km}"> km` : `<input data-seg="${i}" data-key="seconds" type="number" min=".01" step="any" value="${v.seconds}"> s`;
    const demand=v.distance_km!==undefined ? `<input data-seg="${i}" data-key="speed_kmh" type="number" min="0.01" max="150" step=".1" value="${v.speed_kmh}"> km/h` : `<input data-seg="${i}" data-key="demand" type="number" min="0" max="1" step=".01" value="${v.demand}">`;
    html+=`<tr><td>${esc(v.name||'Step '+(i+1))}${v.sleep?' <small>☾</small>':''}</td><td>${duration}</td><td>${demand}</td><td><select data-seg="${i}" data-key="execution"><option value="fixed_pace" ${(v.execution??'fixed_pace')==='fixed_pace'?'selected':''}>Fixed pace</option><option value="fixed_work" ${v.execution==='fixed_work'?'selected':''}>Fixed work</option></select></td><td>${v.distance_km!==undefined ? (v.pace_effort?'Speed-derived':'Rider effort') : `<select data-seg="${i}" data-key="demand_basis"><option value="individual" ${(v.demand_basis??'individual')==='individual'?'selected':''}>Self</option><option value="reference_fitness" ${v.demand_basis==='reference_fitness'?'selected':''}>Ref FIT</option></select>`}</td><td><input data-seg="${i}" data-key="wear" type="number" min="0" max="10" step=".05" value="${v.wear??1}"></td></tr>`;
  }
  html+='</tbody></table><p class="small-help">Demand 0–1. Self: individually chosen effort. Ref FIT: fixed external task adjusted to Fitness. Fixed work: target work is held constant and pace adapts (extra time reported); Fixed pace: stop when the requested rate is infeasible. Fixed-work pacing reserve and time horizon are editable in YAML.</p>';
  $('segments').innerHTML=html;
  wireBeingInputs(actor,false);
  $('segments').querySelectorAll('[data-seg]').forEach(input=>input.addEventListener('change',()=>{
    const idx=Number(input.dataset.seg),key=input.dataset.key;
    const val=['demand_basis','execution'].includes(key)?input.value:Number(input.value);
    actor.segments[idx][key]=val;
    if(working.scenarios[selectedScenario].objective && ['distance_km','speed_kmh'].includes(key)){
      for(const other of Object.values(working.scenarios[selectedScenario].actors))other.segments[idx][key]=val;
    }
    schedule();renderDiff();
  }));
}

function collectDiff(a,b,path='',out=[]){
  if(a===b)return out;
  if(typeof a!=='object'||a===null||typeof b!=='object'||b===null||Array.isArray(a)!==Array.isArray(b)){
    out.push({path,old:a,next:b});return out;
  }
  for(const key of new Set([...Object.keys(a),...Object.keys(b)])){
    collectDiff(a[key],b[key],path?path+'.'+key:key,out);
  }
  return out;
}
function renderDiff(){
  const diff=collectDiff(baseline,working);
  $('change-count').textContent=`${diff.length} edit${diff.length===1?'':'s'}`;
  $('diff').innerHTML=diff.length?diff.slice(0,30).map(x=>{
    const value=x.next===undefined?'[removed]':JSON.stringify(x.next);
    return `<div class="diff-item"><b>${esc(x.path)}</b><div>→ ${esc(value)}</div></div>`;
  }).join(''):'<div style="color:#92a0b1">No changes to the loaded baseline.</div>';
  if(diff.length>30)$('diff').innerHTML+=`<small>… plus ${diff.length-30} more changes</small>`;
}
function schedule(){clearTimeout(rerunTimer);rerunTimer=setTimeout(recompute,200);}
async function recompute(){
  if(!working)return;
  const serial=++requestSequence;
  status('Calculating…');
  try {
    const name=selectedScenario;
    const [next,base]=await Promise.all([
      api('/api/simulate',{scenario:name,config:working}),
      api('/api/simulate',{scenario:name,config:baseline})
    ]);
    if(serial!==requestSequence)return;
    candidateResults=next;baselineResults=base;
    status('Updated');
    drawResults();
  }catch(err){if(serial===requestSequence){status(err.message,true);candidateResults=null;baselineResults=null;}}
}
function diffText(v,w){let d=v-w;return `${d>=0?'+':''}${d.toFixed(1)} pp vs baseline`}
function timeLabel(seconds){if(seconds<120)return fmt(seconds,1)+' s';if(seconds<7200)return fmt(seconds/60,1)+' min';if(seconds<172800)return fmt(seconds/3600,2)+' h';return fmt(seconds/86400,2)+' days';}
function drawResults(){
  if(!candidateResults)return;
  const c=candidateResults.actors[selectedActor], b=baselineResults.actors[selectedActor];
  if(!c){$('error').hidden=false;$('error').textContent='Actor is not present in the baseline';return;}
  for(const [id,metric] of [['q','q'],['b','b'],['m','max_output']]){
    $(id+'-now').textContent=pct(c.summary[metric]);
    $(id+'-delta').textContent=b?diffText(c.summary[metric],b.summary[metric]):'No comparison available';
  }
  const bad=c.summary.first_infeasible_interval_start_s!==null;
  const allOut=c.summary.first_all_out_interval_start_s!==null;
  const paced=c.summary.work_pace_percent!==null && c.summary.work_pace_percent<99.95;
  const scope=working.scenarios[selectedScenario].assessment_kind||'uncalibrated';
  const objective=candidateResults.objective;
  const combat=candidateResults.combat;
  $('feas-now').textContent=combat?(combat.mode==='opposed_grapple'?'Resolved grappling simulated':bad?'Prescribed combat drill not sustained':'Combat fatigue drill completed'):objective?(!objective.mount_and_rider_feasible?'Ride requirement failed':'160 km fatigue-feasible') : bad?'Required output not maintained':(paced?'Optional work completed at reduced pace':(allOut?'Maximal-effort bout simulated':scope==='fixed_duty'?'Mandatory workload sustained':'Scheduled exertion sustained'));
  $('feas-now').style.color=bad?'#bc6540':(allOut?'#366ca5':'#17815b');
  $('feas-extra').textContent=combat?(combat.mode==='opposed_grapple'?`390s completed · seeded contests · ${combat.control_history.length} control changes · ${combat.had_infeasible_actions?'some declarations infeasible':'all declarations feasible'}`:bad?`Unmet effort in ${c.summary.failed_segment} at ${timeLabel(c.summary.total_seconds)}`:`${timeLabel(c.summary.total_seconds)} of scripted action preparation · no wounds or combat winners`):objective?`${fmt(objective.distance_reached_km,1)} / ${objective.distance_km} km · ${fmt(objective.elapsed_hours,2)} / ${objective.deadline_hours} h · ${objective.reason}`: bad?`${c.summary.failed_segment} · halted after ${timeLabel(c.summary.total_seconds)}`:(paced?`Average work pace ${pct(c.summary.work_pace_percent)} of reference · ${timeLabel(c.summary.schedule_delay_seconds)} additional`:(allOut?'Maximum voluntary work adapts to fatigue':'No output cap detected; see assessment scope'));
  $('duration-summary').textContent=`Elapsed ${timeLabel(c.summary.total_seconds)} · nominal ${timeLabel(c.summary.planned_seconds)} · ${c.points.length} samples${bad?' · task not completed':paced?' · fixed work paced down':''}`;
  $('comparison').innerHTML=[['Q reserve','q'],['B reserve','b'],['Current max output','max_output'],['Sustainable output','critical']].map(([label,key])=>`<div class="comparison-row"><span>${label}</span><strong>${b?pct(b.summary[key]):'—'}</strong><strong class="candidate">${pct(c.summary[key])}</strong></div>`).join('');
  if(c.summary.work_pace_percent!==null){
    $('comparison').innerHTML += `<div class="comparison-row"><span>Average delivered work pace</span><strong>${b?.summary.work_pace_percent==null?'—':pct(b.summary.work_pace_percent)}</strong><strong class="candidate">${pct(c.summary.work_pace_percent)}</strong></div>`;
    $('comparison').innerHTML += `<div class="comparison-row"><span>Schedule extension</span><strong>${b?timeLabel(b.summary.schedule_delay_seconds):'—'}</strong><strong class="candidate">${timeLabel(c.summary.schedule_delay_seconds)}</strong></div>`;
  }
  if(objective){
    const horse=candidateResults.actors[objective.joint_actors[0]];
    const stages=horse.summary.checkpoints||[];
    $('comparison').innerHTML+=`<div class="comparison-row"><span>Joint target distance</span><strong>${objective.distance_km} km</strong><strong class="candidate">${fmt(objective.distance_reached_km,2)} km</strong></div>`+
      `<div class="comparison-row"><span>Elapsed / deadline</span><strong>${fmt(objective.elapsed_hours,2)} h</strong><strong class="candidate">${objective.deadline_hours} h limit</strong></div>`+
      stages.map(st=>`<div class="comparison-row"><span>${esc(st.phase)} · ${fmt(st.km,1)} km</span><strong>${fmt(st.elapsed_hours,2)} h</strong><strong class="candidate">Q ${pct(st.q_percent)} · B ${pct(st.b_percent)}</strong></div>`).join('');
  }
  if(combat){
    const by=c.summary.events_by_type||{};
    const rows=Object.entries(by).map(([key,value])=>`<div class="comparison-row"><span>${esc(key)}</span><strong>—</strong><strong class="candidate">${value}</strong></div>`).join('');
    $('comparison').innerHTML+=rows;
    if(combat.mode==='opposed_grapple'){
      const forced=by['seconds recover']||0;
      const grappleSecs=by['seconds grapple']||0;
      const denied=Object.entries(by).filter(([k])=>k.startsWith('infeasible ')).reduce((sum,[,v])=>sum+v,0);
      $('comparison').innerHTML+=`<p class="small-help">Interpretation: ${forced} seconds of forced recovery, ${grappleSecs} seconds of Grapple effort, ${denied} infeasible action declarations. A Being with lower Fitness may finish with more Q because it was unable to keep exerting itself. The same seed does not mean identical resolved action sequences.</p>`;
    }
    $('combat-details').hidden=false;
    const liveMode=combat.mode==='opposed_grapple';
    const intro=liveMode?`<h3>Resolved Grapple · physical-check fatigue test</h3><p>Seed ${combat.seed}. Contest fatigue ${combat.fatigue_contest_penalty_enabled?'on':'off'} (universal table, sensitivity 5). Opposed d20 Touch, opposed 3d6 Grab, Grapple control, Escape and Break hold are resolved. Physical grips remain distinct from Grapple. No hits, damage, movement, takedowns or pins. Failed action declarations do not end either bout.</p><p>Current controller: <b>${esc(combat.grappling_position||'None')}</b> · Physical grips: ${esc(JSON.stringify(combat.physical_grips))} · ${combat.control_history.length} control changes.</p>`:`<h3>Combat calibration timeline</h3><p>No dice, wounds, damage, position transitions or winners. Action preparation is timed; fatigue state changes are committed after same-second resolution. All workloads are editable assumptions.</p>`;
    const details=e=>liveMode?(e.events||[]).map(z=>{
      if(z.check){const k=z.check;return `${z.actor||'Opposed '+z.action}: ${z.action} — ${Object.entries(k.scores).map(([n,v])=>`${n} ${v}`).join(' vs ')}; fatigue ${esc(JSON.stringify(k.fatigue_penalties||{}))}; winner ${k.winner||'tie'}; ${z.controller_before===undefined?'':`Grapple: ${z.controller_before||'none'} → ${z.controller_after||'none'}`}`;}
      return `${z.actor||''} ${z.action||''} ${z.success===undefined?'':z.success?'success':'failure'} ${z.reason||''}`;
    }).join(' | '):(e.events||[]).map(z=>z.actor+': '+(z.action||z.kind)).join('; ');
    $('combat-details').innerHTML=intro+
      `<div class="combat-phases">${combat.phases.map(ph=>`<span>${esc(ph.name)} · ${fmt(ph.start_s,0)}–${fmt(ph.end_s,0)} s</span>`).join('')}</div>`+
      `<details><summary>Action resolution log (${combat.event_log.length} seconds with events)</summary><div class="combat-log">${combat.event_log.filter(x=>combat.mode!=='opposed_grapple'||x.outcome.includes('infeasible')||x.outcome.includes('resolved')||x.outcome.includes('bout begins')).slice(0,400).map(x=>`<div><b>${fmt(x.second,0)} s</b> ${esc(x.outcome)} ${esc(details(x))} ${esc((x.defenses||[]).map(d=>d.defender+' '+d.defense+' vs '+d.against).join('; '))}</div>`).join('')}</div></details>`;
  }else{$('combat-details').hidden=true;$('combat-details').innerHTML='';}
  renderBeing();
  const feedback=$('being-contest-feedback');
  const live=working.scenarios[selectedScenario]?.grapple_encounter;
  if(live && c){
    const q=c.summary.q/100, b=c.summary.b/100;
    const sustainable=.60*(.25+.75*b), peak=1-.45*(1-b);
    const standard=sustainable+(peak-sustainable)*(1-(1-q)**2);
    const d=c.summary.check_penalty ?? (live.fatigue_contest_penalty_enabled?Math.floor(5*(1-standard)+.50000001):0);
    feedback.textContent=`Universal physical-check penalty −${d} · Q ${pct(c.summary.q)} · B ${pct(c.summary.b)} · feasibility output ${pct(c.summary.max_output)}`;
  }else feedback.textContent='Not used for this scenario';
  drawChart();
}
function getChartAxis(sec){const v=$('time-axis').value;if(v==='seconds'||v==='minutes'||v==='hours')return v;return sec<=180?'seconds':sec<=10800?'minutes':'hours';}
function drawChart(){
  if(!candidateResults)return;
  const canv=$('chart'),rect=canv.getBoundingClientRect();if(rect.width<50)return;
  const dpr=window.devicePixelRatio||1;
  canv.width=Math.round(rect.width*dpr);canv.height=Math.round(rect.height*dpr);
  const ctx=canv.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);
  const W=rect.width,H=rect.height;
  ctx.clearRect(0,0,W,H);
  const box={l:48,r:17,t:23,b:40},plotW=W-box.l-box.r,plotH=H-box.t-box.b;
  const c=candidateResults.actors[selectedActor]; const base=baselineResults.actors[selectedActor];
  const fullX=Math.max(1,c.summary.planned_seconds,c.summary.total_seconds,base?.summary.total_seconds??0);
  const windowChoice=$('chart-window').value;
  const maxX=windowChoice==='all'?fullX:windowChoice==='auto'&& !c.summary.completed
    ? Math.min(fullX,Math.max(3600,c.summary.total_seconds*1.25))
    : windowChoice==='auto'?fullX:Math.min(fullX,Number(windowChoice));
  const ax=getChartAxis(maxX);
  const x=t=>box.l+plotW*t/maxX, y=value=>box.t+plotH*(100-value)/100;
  ctx.font='11px ui-sans-serif,system-ui';ctx.textBaseline='middle';ctx.textAlign='right';
  for(let value=0;value<=100;value+=20){
    ctx.beginPath();ctx.strokeStyle='#e9eef5';ctx.lineWidth=1;ctx.moveTo(box.l,y(value));ctx.lineTo(W-box.r,y(value));ctx.stroke();ctx.fillStyle='#8c9aaa';ctx.fillText(String(value),box.l-11,y(value));
  }
  ctx.textAlign='center';ctx.fillStyle='#8c9aaa';
  for(let k=0;k<=5;k++){
    const t=maxX*k/5;
    const val=ax==='seconds'?t:ax==='minutes'?t/60:t/3600;
    ctx.fillText(fmt(val,1),x(t),H-23);
  }
  ctx.fillText(ax+' from start',W/2,H-7);
  const draw=(arr,key,color,dashed=false)=>{
    if(!arr)return;
    ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=dashed?1.5:2.5;ctx.globalAlpha=dashed?.35:1;ctx.setLineDash(dashed?[5,5]:[]);
    for(let i=0;i<arr.length;i++){
      const p=arr[i],X=x(p.seconds),Y=y(p[key]);
      if(i===0)ctx.moveTo(X,Y);else ctx.lineTo(X,Y);
    }
    ctx.stroke();ctx.globalAlpha=1;ctx.setLineDash([]);
  };
  ctx.save();ctx.beginPath();ctx.rect(box.l,box.t,plotW,plotH);ctx.clip();
  const colors=[['q','#2563eb'],['b','#059669'],['max_output','#ea580c'],['actual','#9a4dd1']];
  if($('show-base').checked&&base)for(const [key,col] of colors)draw(base.points,key,col,true);
  for(const [key,col] of colors)draw(c.points,key,col,false);
  if(!c.summary.completed){
    const xFail=x(c.summary.total_seconds);
    ctx.beginPath();ctx.strokeStyle='#b45309';ctx.lineWidth=1.6;ctx.setLineDash([3,4]);ctx.moveTo(xFail,box.t);ctx.lineTo(xFail,box.t+plotH);ctx.stroke();ctx.setLineDash([]);
  }
  ctx.restore();
  canv.onmousemove=e=>{
    const off=e.clientX-canv.getBoundingClientRect().left;
    if(off<box.l||off>W-box.r){$('hover-info').style.display='none';return;}
    const t=maxX*(off-box.l)/plotW;
    if(t>c.summary.total_seconds){$('hover-info').style.display='none';return;}
    let lo=0,hi=c.points.length-1;
    while(lo<hi){const mid=Math.floor((lo+hi)/2);if(c.points[mid].seconds<t)lo=mid+1;else hi=mid;}
    const idx=Math.max(0,lo>0 && Math.abs(c.points[lo-1].seconds-t)<Math.abs(c.points[lo].seconds-t)?lo-1:lo);
    const point=c.points[idx];
    $('hover-info').innerHTML=`<b>${timeLabel(point.seconds)}</b> · ${esc(point.segment)}<div>Q ${pct(point.q)} · B ${pct(point.b)} · M ${pct(point.max_output)} · realized effort ${pct(point.actual)}</div>`;
    $('hover-info').style.display='block';
  };
  canv.onmouseleave=()=>$('hover-info').style.display='none';
}
function wire(){
  $('profile').addEventListener('change',()=>{selectedProfile=$('profile').value;renderParams();renderWorkloadParams();});
  $('scenario').addEventListener('change',()=>{selectedScenario=$('scenario').value;selectedActor='';updateActorSelection();selectedProfile=working.scenarios[selectedScenario].actors[selectedActor].profile;$('profile').value=selectedProfile;renderParams();renderWorkloadParams();schedule();});
  $('actor').addEventListener('change',()=>{selectedActor=$('actor').value;selectedProfile=working.scenarios[selectedScenario].actors[selectedActor].profile;$('profile').value=selectedProfile;renderParams();renderWorkloadParams();renderScenarioInputs();drawResults();});
  $('show-base').addEventListener('change',drawChart);
  $('chart-window').addEventListener('change',drawChart);
  $('time-axis').addEventListener('change',drawChart);
  $('clear-overrides').addEventListener('click',()=>{working.profiles[selectedProfile].parameters={};renderParams();renderDiff();schedule();});
  $('reset-button').addEventListener('click',()=>{working=clone(baseline);updateSelections();renderDiff();schedule();});
  $('load-button').addEventListener('click',()=>$('upload').click());
  $('upload').addEventListener('change',async e=>{
    const file=e.target.files?.[0];if(!file)return;
    try{const yaml=await file.text(); const r=await api('/api/parse',{yaml});baseline=clone(r.config);working=clone(r.config);selectedScenario='';selectedActor='';selectedProfile='';updateSelections();renderDiff();schedule();status('YAML loaded');}
    catch(err){status('Import rejected: '+err.message,true);}
    e.target.value='';
  });
  $('manual-card-button').addEventListener('click',async()=>{
    try {
      const result=await api('/api/manual-card',{config:working,scenario:selectedScenario,actor:selectedActor});
      const blob=new Blob([result.markdown],{type:'text/markdown;charset=utf-8'});
      const url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url;a.download='fatigue-manual-card-'+selectedActor.toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.md';
      document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
      status('Generated reference card for '+selectedActor);
    }catch(err){status('Manual card failed: '+err.message,true);}
  });
  $('save-button').addEventListener('click',async()=>{
    try{
      const r=await api('/api/export',{config:working});
      const blob=new Blob([r.yaml],{type:'text/yaml;charset=utf-8'});
      const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='fatigue-config-candidate.yaml';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);status('YAML exported');
    }catch(err){status('Export failed: '+err.message,true);}
  });
  window.addEventListener('resize',drawChart);
}
function assertMatchingBuild(serverBuild){
  // Read the expected build from the HTML served to this browser, rather
  // than maintaining a third copy of the release identifier in JavaScript.
  const expected = String($('build-id')?.textContent || '').replace(/^BUILD\s+/, '').trim();
  if (!expected || serverBuild !== expected){
    throw Error('Unexpected server build: ' + String(serverBuild || 'unknown') +
      '; this interface expects ' + (expected || 'a build label') +
      '. Stop the old server and start this release.');
  }
}
async function boot(){
  wire();try{
    const r=await api('/api/default');
    assertMatchingBuild(r.build);
    workloadSpec=r.schema.workload_scaling||{};
    paramSpec=Object.entries(r.schema.parameters).map(([key,p])=>[key,p.label,p.slider_min,p.slider_max,p.step,p.description,p.unit]);
    defaultParameters=Object.fromEntries(Object.entries(r.schema.parameters).map(([key,p])=>[key,p.default]));
    baseline=clone(r.config);working=clone(r.config);
    updateSelections();renderDiff();await recompute();
  }catch(err){status('Could not start: '+err.message,true);}
}
document.addEventListener('DOMContentLoaded',boot);
