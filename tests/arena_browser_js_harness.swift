import Foundation
import JavaScriptCore

guard CommandLine.arguments.count == 4 else {
    fputs("usage: arena_browser_js_harness.swift PAGE_HTML INITIAL_VIEW_JSON TARGET_CELL_JSON\n", stderr)
    exit(2)
}

func read(_ path: String) -> String {
    (try? String(contentsOfFile: path, encoding: .utf8)) ?? ""
}

let html = read(CommandLine.arguments[1])
let initialView = read(CommandLine.arguments[2])
let targetCell = read(CommandLine.arguments[3])
guard let start = html.range(of: "<script>"),
      let end = html.range(of: "</script>", range: start.upperBound..<html.endIndex) else {
    fputs("generated page has no inline script\n", stderr)
    exit(2)
}
let pageScript = String(html[start.upperBound..<end.lowerBound])

let context = JSContext()!
context.exceptionHandler = { _, exception in
    fputs("JavaScript error: \(exception?.toString() ?? "unknown")\n", stderr)
}
let prelude = #"""
var __elements = Object.create(null);
var __canvasContext = new Proxy({}, {get:(o,k)=>o[k]||(o[k]=function(){})});
function __element(id){
  if(!__elements[id]){
    const e={id,value:id==='xp'?'10000':id==='width'?'10':id==='height'?'5':id==='rate'?'walk':'turn',
      disabled:false,textContent:'',listeners:Object.create(null),clientWidth:800,clientHeight:520,
      addEventListener(name,fn){this.listeners[name]=fn},getContext(){return __canvasContext},
      getBoundingClientRect(){return {left:0,top:0}}};
    __elements[id]=e;
  }
  return __elements[id];
}
var document={getElementById:__element};
var window={devicePixelRatio:1,addEventListener:function(){}};
var __serverState={state:'empty'};
var __initialView=__INITIAL_VIEW__;
var __targetCell=__TARGET_CELL__;
var __calls=[];
function __response(){return {ok:true,json:()=>Promise.resolve(JSON.parse(JSON.stringify(__serverState)))}}
function fetch(path,options={}){
  const body=options.body===undefined?null:JSON.parse(options.body);
  __calls.push({path,method:options.method||'GET',body,headers:options.headers||{}});
  if(path==='/api/generated/generate')__serverState=JSON.parse(JSON.stringify(__initialView));
  else if(path==='/api/generated/destination'){
    const m=__serverState.map, b=body;
    const x=m.origin_offset_meters[0]+b.column*m.column_step_meters;
    const y=m.origin_offset_meters[1]+b.row*m.row_step_meters+(b.column%2)*m.odd_column_offset_meters;
    __serverState.movement_plan={destination_cell:{column:b.column,row:b.row},
      destination_position_meters:{x,y,z:__serverState.player.position_meters.z},
      rate:b.rate,facing_policy:b.facing_policy,remaining_distance_meters:1};
    __serverState.advance_available=true;__serverState.movement_outcome='destination_selected';
  } else if(path==='/api/generated/advance'){
    __serverState.time_seconds+=1;__serverState.movement_outcome='progressed';
  }
  return Promise.resolve(__response());
}
"""#
let preparedPrelude = prelude
    .replacingOccurrences(of: "__INITIAL_VIEW__", with: initialView)
    .replacingOccurrences(of: "__TARGET_CELL__", with: targetCell)
context.evaluateScript(preparedPrelude)
context.evaluateScript(pageScript)
let scenario = #"""
globalThis.__done=false;globalThis.__failure='';globalThis.__result='';
(async()=>{
  await Promise.resolve();
  await __element('generate').onclick();
  __element('rate').value='sprint';
  await __element('rate').listeners.change();
  const m=currentView.map,c=__element('map'),cell=__targetCell;
  const minX=0,maxX=m.origin_offset_meters[0]+(m.width_cells-1)*m.column_step_meters+m.hex_vertex_offsets_meters[0][0];
  const minY=0,maxY=m.height_cells*m.row_step_meters+(m.width_cells>1?m.odd_column_offset_meters:0);
  const scale=Math.min((c.clientWidth-24)/(maxX-minX),(c.clientHeight-24)/(maxY-minY));
  const ox=(c.clientWidth-(maxX-minX)*scale)/2,oy=(c.clientHeight-(maxY-minY)*scale)/2;
  const cx=m.origin_offset_meters[0]+cell.column*m.column_step_meters;
  const cy=m.origin_offset_meters[1]+cell.row*m.row_step_meters+(cell.column%2)*m.odd_column_offset_meters;
  await c.listeners.click({clientX:ox+(cx-minX)*scale,clientY:c.clientHeight-oy-(cy-minY)*scale});
  __element('rate').value='walk';
  await __element('rate').listeners.change();
  __element('rate').value='sprint';
  const optionRequest=__element('rate').listeners.change();
  const advanceRequest=__element('advance').onclick();
  await Promise.all([optionRequest,advanceRequest]);
  globalThis.__result=JSON.stringify({calls:__calls,plan:currentView.movement_plan,
    time:currentView.time_seconds,status:__element('movementStatus').textContent,error:__element('error').textContent});
})().then(()=>globalThis.__done=true).catch(e=>{globalThis.__failure=String(e);globalThis.__done=true});
"""#
context.evaluateScript(scenario)
let deadline = Date().addingTimeInterval(8)
while context.globalObject?.forProperty("__done")?.toBool() != true && Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.01))
}
if context.globalObject?.forProperty("__done")?.toBool() != true {
    fputs("JavaScript handler harness timed out\n", stderr)
    exit(1)
}
if let failure = context.globalObject?.forProperty("__failure")?.toString(), !failure.isEmpty {
    fputs("JavaScript handler harness failed: \(failure)\n", stderr)
    exit(1)
}
print(context.globalObject?.forProperty("__result")?.toString() ?? "{}")
