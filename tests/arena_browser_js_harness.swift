import Foundation
import JavaScriptCore

guard CommandLine.arguments.count == 5 else {
    fputs("usage: arena_browser_js_harness.swift PAGE_HTML INITIAL_VIEW_JSON TARGET_CELL_JSON PICKED_UP_VIEW_JSON\n", stderr)
    exit(2)
}

func read(_ path: String) -> String {
    (try? String(contentsOfFile: path, encoding: .utf8)) ?? ""
}

let html = read(CommandLine.arguments[1])
let initialView = read(CommandLine.arguments[2])
let targetCell = read(CommandLine.arguments[3])
let pickedUpView = read(CommandLine.arguments[4])
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
      children:[],dataset:Object.create(null),replaceChildren(){this.children=[]},appendChild(e){this.children.push(e)},
      addEventListener(name,fn){this.listeners[name]=fn},getContext(){return __canvasContext},
      getBoundingClientRect(){return {left:0,top:0}}};
    __elements[id]=e;
  }
  return __elements[id];
}
var document={getElementById:__element,createElement(tag){return {tagName:tag,textContent:'',dataset:Object.create(null),listeners:Object.create(null),children:[],appendChild(e){this.children.push(e)},replaceChildren(){this.children=[]},addEventListener(name,fn){this.listeners[name]=fn}}}};
var window={devicePixelRatio:1,addEventListener:function(){}};
var __serverState={state:'empty'};
var __initialView=__INITIAL_VIEW__;
var __targetCell=__TARGET_CELL__;
var __pickedUpView=__PICKED_UP_VIEW__;
var __calls=[];
var __lastPlan=null;
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
    __lastPlan=JSON.parse(JSON.stringify(__serverState.movement_plan));
    __serverState.advance_available=true;__serverState.movement_outcome='destination_selected';
  } else if(path==='/api/generated/advance'){
    __serverState.time_seconds+=1;
    if(__serverState.movement_plan){
      __serverState.player.position_meters=JSON.parse(JSON.stringify(__serverState.movement_plan.destination_position_meters));
      __serverState.player.cell=JSON.parse(JSON.stringify(__serverState.movement_plan.destination_cell));
      if(__serverState.character){__serverState.character.movement.position_meters=JSON.parse(JSON.stringify(__serverState.player.position_meters));__serverState.character.movement.cell=JSON.parse(JSON.stringify(__serverState.player.cell));__serverState.character.movement.selected_plan=null;}
      __serverState.movement_plan=null;__serverState.movement_outcome='arrived';
      for(const e of __serverState.entities||[])if(e.category==='object'&&e.cell&&e.cell.column===__serverState.player.cell.column&&e.cell.row===__serverState.player.cell.row)e.pickup_available=true;
    }else if(__serverState.pickup_action&&__serverState.pickup_action.status==='executing'){
      __serverState.pickup_action={name:'Pick up',status:'completed',outcome:'success'};
      const e=__serverState.entities.find(row=>row.handle===__serverState.selected_entity.handle);
      if(e){e.present_state='carried';e.position_meters=null;e.cell=null;e.pickup_available=false;}
      if(__serverState.character){__serverState.character.inventory=JSON.parse(JSON.stringify(__pickedUpView.character.inventory));__serverState.character.movement.position_meters=JSON.parse(JSON.stringify(__serverState.player.position_meters));__serverState.character.movement.cell=JSON.parse(JSON.stringify(__serverState.player.cell));}
    }
    __serverState.movement_outcome=__serverState.movement_outcome||'progressed';
  } else if(path==='/api/generated/inspect'){
    __serverState.selected_entity=__serverState.entities.find(e=>e.handle===body.handle)||null;
    if(__serverState.selected_entity&&__serverState.selected_entity.category==='object')__serverState.selected_entity.pickup_available=true;
  } else if(path==='/api/generated/pickup'){
    __serverState.pickup_action={name:'Pick up',status:'executing',outcome:null};
  } else if(path==='/api/generated/rename-entity'){
    const e=__serverState.entities.find(row=>row.handle===body.handle);
    if(e){e.name=body.name;__serverState.selected_entity=e;}
  }
  return Promise.resolve(__response());
}
"""#
let preparedPrelude = prelude
    .replacingOccurrences(of: "__INITIAL_VIEW__", with: initialView)
    .replacingOccurrences(of: "__TARGET_CELL__", with: targetCell)
    .replacingOccurrences(of: "__PICKED_UP_VIEW__", with: pickedUpView)
context.evaluateScript(preparedPrelude)
context.evaluateScript(pageScript)
let scenario = #"""
globalThis.__done=false;globalThis.__failure='';globalThis.__result='';
(async()=>{
  await Promise.resolve();
  await __element('generate').onclick();
  if(__element('characterPanel').hidden)throw Error('generated character sheet remained hidden');
  __element('rate').value='sprint';
  await __element('rate').listeners.change();
  const initialObject=currentView.entities.find(e=>e.type==='Dagger'&&e.category==='object');
  if(!initialObject)throw Error('generated object was not visible on the map');
  if(!__element('characterSummary').children.length)throw Error('generated character sheet was not rendered');
  if(!__element('characterInventory').children.some(e=>e.textContent==='No items carried'))throw Error('initial inventory is not shown as empty');
  const c=__element('map');
  await c.listeners.click({clientX:mapView.toX(initialObject.position_meters.x),
    clientY:mapView.toY(initialObject.position_meters.y)});
  __element('entityName').value='Renamed Dagger';
  await __element('renameEntity').onclick();
  const m=currentView.map,cell=__targetCell;
  const minX=0,maxX=m.origin_offset_meters[0]+(m.width_cells-1)*m.column_step_meters+m.hex_vertex_offsets_meters[0][0];
  const minY=0,maxY=m.height_cells*m.row_step_meters+(m.width_cells>1?m.odd_column_offset_meters:0);
  const scale=Math.min((c.clientWidth-24)/(maxX-minX),(c.clientHeight-24)/(maxY-minY));
  const ox=(c.clientWidth-(maxX-minX)*scale)/2,oy=(c.clientHeight-(maxY-minY)*scale)/2;
  const cx=m.origin_offset_meters[0]+cell.column*m.column_step_meters;
  const cy=m.origin_offset_meters[1]+cell.row*m.row_step_meters+(cell.column%2)*m.odd_column_offset_meters;
  await c.listeners.click({clientX:ox+(cx-minX)*scale+24,clientY:c.clientHeight-oy-(cy-minY)*scale});
  __element('rate').value='walk';
  await __element('rate').listeners.change();
  __element('rate').value='sprint';
  const optionRequest=__element('rate').listeners.change();
  const advanceRequest=__element('advance').onclick();
  await Promise.all([optionRequest,advanceRequest]);
  const visibleObject=__element('entities').children.find(e=>e.textContent.includes('Renamed Dagger'));
  if(!visibleObject)throw Error('renamed object disappeared after movement');
  await visibleObject.listeners.click();
  if(__element('pickup').disabled)throw Error('same-hex object was not pickup-eligible after arrival');
  await __element('pickup').onclick();
  await __element('advance').onclick();
  const carried=__element('entities').children.find(e=>e.textContent.includes('Renamed Dagger'));
  if(!carried)throw Error('carried display name was not retained');
  if(!__element('characterInventory').children.some(e=>e.textContent.includes('Renamed Dagger')&&e.textContent.includes('carried; not readied')))throw Error('committed inventory did not refresh with carried non-readied Object');
  await carried.listeners.click();
  globalThis.__result=JSON.stringify({calls:__calls,plan:__lastPlan,
    time:currentView.time_seconds,status:__element('movementStatus').textContent,error:__element('error').textContent,
    entityDetails:__element('entityDetails').textContent,pickupStatus:__element('pickupStatus').textContent,
    renameStatus:__element('renameStatus').textContent,finalEntity:currentView.selected_entity,
    characterSummary:__element('characterSummary').children.map(g=>g.children.map(e=>e.textContent)),
    characterInventory:__element('characterInventory').children.map(e=>e.textContent)});
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
