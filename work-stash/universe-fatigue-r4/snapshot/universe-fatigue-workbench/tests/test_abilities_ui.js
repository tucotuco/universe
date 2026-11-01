/* Minimal DOM smoke test: executes the release's actual browser rendering function. */
const fs = require('fs');
const vm = require('vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const app = fs.readFileSync(path.join(__dirname, '../static/app.js'),'utf8');
const nodes = Object.create(null);
const document = {
  getElementById(id){ return nodes[id] ??= {innerHTML:'',textContent:''}; },
  addEventListener(){},
};
const context = vm.createContext({document, console});
vm.runInContext(app,context);
vm.runInContext(`
working={
 profiles:{human:{parent:null,workload_scaling:{reference_fitness:12,fitness_exponent:1}}},
 scenarios:{legionary:{actors:{Legionary:{
 profile:'human', fitness:10.5, run_level:0,
 abilities:{strength:13,dexterity:12,constitution:16,intelligence:10,wisdom:11,charisma:10},
 segments:[{name:'Loaded march',demand:0.37,demand_basis:'reference_fitness'}]
 }}}}
};
selectedScenario='legionary'; selectedActor='Legionary';
candidateResults={actors:{Legionary:{}}};
renderBeing();
`,context);
assert.match(nodes['being-abilities'].innerHTML,/10\.5/);
assert.match(nodes['being-abilities'].innerHTML,/FIT/);
assert.match(nodes['being-abilities'].innerHTML,/13/);
assert.match(nodes['being-abilities'].innerHTML,/STR/);
assert.match(nodes['being-workload'].innerHTML,/42\.3%/);
assert.equal(nodes['being-title'].textContent,'Legionary');
console.log('PASS: Being abilities and effective workload render using bundled application code');
