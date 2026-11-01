// Prevent server/browser release mismatch (R4.7 startup regression).
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'static/index.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'static/app.js'), 'utf8');
const py = fs.readFileSync(path.join(root, 'workbench.py'), 'utf8');
const marker = html.match(/id="build-id"[^>]*>BUILD ([^<]+)</);
const server = py.match(/^BUILD_ID = "([^"]+)"/m);
assert.ok(marker && server, 'Both build identifiers must be declared');
assert.equal(marker[1], server[1], 'HTML must match server build');
const document = {
  getElementById(id){return id === 'build-id' ? {textContent:'BUILD '+marker[1]} : null;},
  addEventListener(){}
};
const ctx = vm.createContext({document, console});
vm.runInContext(js, ctx);
assert.doesNotThrow(()=>vm.runInContext('assertMatchingBuild('+JSON.stringify(server[1])+')',ctx));
assert.throws(()=>vm.runInContext('assertMatchingBuild("OBSOLETE RELEASE")',ctx),/Unexpected server build.*expects/);
console.log('PASS: server, HTML, JavaScript startup contract, including stale-server failure');
