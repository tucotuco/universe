const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('node:assert/strict');
const app=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const yaml=fs.readFileSync(path.join(__dirname,'../config.yaml'),'utf8');
// Use a tiny scenario fixture instead of a YAML parser dependency.
const nodeMap=Object.create(null);
const document={getElementById(id){return nodeMap[id]??=( {innerHTML:'',textContent:'',value:'',addEventListener(){},querySelectorAll(){return [];}} );},addEventListener(){}};
const context=vm.createContext({document,console});vm.runInContext(app,context);
const script=`
const prof={human:{parent:null,scaling:'human_r4',parameters:{},workload_scaling:{reference_fitness:12,fitness_exponent:1}}};
const fixture={profile:'human',fitness:12,run_level:0,abilities:{strength:13,dexterity:12,constitution:14},
 improved_grapple:4,escape_artist:2,attack_level:2,defense_level:2,armor_check_penalty:0};
working={profiles:prof,scenarios:{combat_d_live_grapple:{actors:{'Grappler Fitness 12':fixture,'Grappler Fitness 16':{...fixture,fitness:16,abilities:{...fixture.abilities,constitution:18}}},
 grapple_encounter:{seed:20261026,fatigue_contest_penalty_enabled:true,costs:{grapple:{demand:.7,wear:1.1,demand_basis:'reference_fitness',fitness_exponent:.35},touch:{demand:.56,wear:1,demand_basis:'reference_fitness',fitness_exponent:.35}},
 phases:[{name:'Bout 1',seconds:180},{name:'Rest',seconds:30},{name:'Bout 2',seconds:180}]}}}};
selectedScenario='combat_d_live_grapple';selectedActor='Grappler Fitness 12';
candidateResults={actors:{'Grappler Fitness 12':{summary:{q:25,b:98,max_output:76},points:[]}}};
renderBeing();renderScenarioInputs();
`;
vm.runInContext(script,context);
assert.match(nodeMap['being-abilities'].innerHTML,/FIT/);
assert.match(nodeMap['being-abilities'].innerHTML,/12/);
assert.match(nodeMap['being-training'].textContent,/Grapple 4/);
assert.match(nodeMap['being-workload'].innerHTML,/grapple/);
assert.match(nodeMap['segments'].innerHTML,/grapple-seed/);
assert.match(nodeMap['segments'].innerHTML,/grapple-fatigue-enabled/);
assert.doesNotMatch(nodeMap['segments'].innerHTML,/grapple-fatigue-scale/);
assert.match(nodeMap['segments'].innerHTML,/Universal Q\/B physical-check table/);
assert.match(nodeMap['segments'].innerHTML,/data-gcost="grapple"/);
assert.match(nodeMap['segments'].innerHTML,/improved_grapple/);
assert.match(nodeMap['segments'].innerHTML,/0.7/);
console.log('PASS: R4.7 resolved-grapple scenario, skill inputs, shared costs, seed, Being abilities render');
