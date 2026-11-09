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
      children:[],dataset:Object.create(null),replaceChildren(){this.children=[]},appendChild(e){this.children.push(e)},append(...items){this.children.push(...items)},
      addEventListener(name,fn){this.listeners[name]=fn},showModal(){this.open=true},close(){this.open=false;if(this.listeners.close)this.listeners.close()},focus(){this.focused=true},getContext(){return __canvasContext},
      getBoundingClientRect(){return {left:0,top:0}}};
    __elements[id]=e;
  }
  return __elements[id];
}
var document={getElementById:__element,createElement(tag){return {tagName:tag,id:'',value:'',maxLength:0,type:'',className:'',textContent:'',dataset:Object.create(null),listeners:Object.create(null),children:[],appendChild(e){this.children.push(e)},append(...items){this.children.push(...items)},replaceChildren(){this.children=[]},addEventListener(name,fn){this.listeners[name]=fn},focus(){this.focused=true}}}};
function __find(root,id){if(root.id===id)return root;for(const child of root.children||[]){const found=__find(child,id);if(found)return found}return null}
function __findHandle(root,handle){if(root.dataset&&root.dataset.handle===handle)return root;for(const child of root.children||[]){const found=__findHandle(child,handle);if(found)return found}return null}
function __text(root){return [root.textContent||'',...(root.children||[]).map(__text)].join(' ')}
var window={devicePixelRatio:1,addEventListener:function(){}};
var __serverState={state:'empty'};
var __initialView=__INITIAL_VIEW__;
var __targetCell=__TARGET_CELL__;
var __pickedUpView=__PICKED_UP_VIEW__;
var __calls=[];
var __lastPlan=null;
function __refreshActionCatalog(){
  const entries=__serverState.action_catalog&&__serverState.action_catalog.entries||[];
  const run=entries.find(e=>e.name==='Run');
  if(run&&run.status!=='not_implemented'){run.status=__serverState.run_available?'available':'unavailable';run.reason=__serverState.run_available?'The native target-free Run Choice can activate this Arena.':'Run is only accepted as the first player Action; this Encounter is already activated.'}
  const pickup=entries.find(e=>e.name==='Pick up');
  if(pickup){const target=__serverState.selected_entity;pickup.target=target?{handle:target.handle,name:target.name,type:target.type,present_state:target.present_state}:null;if(__serverState.pickup_action&&__serverState.pickup_action.status==='executing'){pickup.status='unavailable';pickup.reason='A native Pick up Action is already resolving.'}else if(!target||target.category!=='object'||target.present_state!=='ground'){pickup.status='unavailable';pickup.reason='Select a currently perceived ground Object first.'}else if(!__serverState.run_available&&target.pickup_available){pickup.status='available';pickup.reason='Native one-second Pick up is currently available for this Object.'}else{pickup.status='unavailable';pickup.reason=target.pickup_unavailable_reason||'Move into the same hex as this Object before choosing Pick up.'}}
}
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
  } else if(path==='/api/generated/run'){
    __serverState.run_available=false;__serverState.advance_available=true;
    __serverState.player_action={name:'Run',status:'executing',outcome:null};__refreshActionCatalog();
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
    }else if(__serverState.player_action&&__serverState.player_action.status==='executing'){
      __serverState.player_action={name:'Run',status:'completed',outcome:'no_movement'};
    }
    __serverState.advance_available=false;__refreshActionCatalog();
    __serverState.movement_outcome=__serverState.movement_outcome||'progressed';
  } else if(path==='/api/generated/inspect'){
    __serverState.selected_entity=__serverState.entities.find(e=>e.handle===body.handle)||null;
    if(__serverState.selected_entity&&__serverState.selected_entity.category==='object'){
      const e=__serverState.selected_entity,p=__serverState.player.cell;
      e.pickup_available=!__serverState.run_available&&e.present_state==='ground'&&e.cell&&p&&e.cell.column===p.column&&e.cell.row===p.row;
      e.pickup_unavailable_reason=e.pickup_available?'':'Move into the same hex as this Object before choosing Pick up.';
    }
    __refreshActionCatalog();
  } else if(path==='/api/generated/pickup'){
    __serverState.pickup_action={name:'Pick up',status:'executing',outcome:null};
    __refreshActionCatalog();
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
  const c=__element('map'),dialog=__element('entityDialog');
  if(__element('characterPanel').children.length)throw Error('expanded character sheet remains in page');
  __element('characterButton').listeners.click({currentTarget:__element('characterButton')});
  if(!dialog.open||__element('dialogTitle').textContent!=='Your Being — Character')throw Error('Character button did not open player popup');
  let body=__text(__element('dialogBody'));
  if(!body.includes('Identity and experience')||!body.includes('Skills and recorded practice')||!body.includes('No items carried'))throw Error('native character projection missing from player popup');
  if(!body.includes('Age is not represented')||!body.includes('Class XP'))throw Error('unsupported native fields are not labeled');
  const actionDisclosure=__find(__element('dialogBody'),'actionSelector');
  if(!actionDisclosure||!__text(actionDisclosure).includes('56 potential'))throw Error('native Action catalog is not displayed in the player popup');
  actionDisclosure.open=true;actionDisclosure.listeners.toggle();
  if(!__find(__element('dialogBody'),'actionReadyWeapon').disabled)throw Error('unsupported Ready weapon was enabled');
  if(!__find(__element('dialogBody'),'actionPickup').disabled)throw Error('Pick up was enabled without an authorized target');
  if(__find(__element('dialogBody'),'actionRun').disabled)throw Error('native first-choice Run was unavailable');
  await __find(__element('dialogBody'),'actionRun').listeners.click();
  if(!__find(__element('dialogBody'),'actionRun').disabled)throw Error('Run remained available after native activation');
  await __element('advance').onclick();
  if(currentView.time_seconds!==1||!currentView.player_action||currentView.player_action.status!=='completed')throw Error('Run did not resolve through native one-second advancement');
  __element('rate').value='sprint';await __element('rate').listeners.change();
  const movementCount=()=>__calls.filter(call=>call.path==='/api/generated/destination').length;
  let before=movementCount(),p=currentView.player.position_meters;
  await c.listeners.click({clientX:mapView.toX(p.x),clientY:mapView.toY(p.y)});
  if(movementCount()!==before||__element('dialogTitle').textContent!=='Your Being — Character')throw Error('player marker changed destination or missed popup');
  const opponent=currentView.entities.find(e=>e.category==='being');
  if(!opponent)throw Error('opponent evidence missing');
  before=movementCount();await c.listeners.click({clientX:mapView.toX(opponent.position_meters.x),clientY:mapView.toY(opponent.position_meters.y)});
  body=__text(__element('dialogBody'));
  if(movementCount()!==before||!body.includes(opponent.type)||!body.includes(opponent.present_state)||body.includes('Total native XP')||body.includes('inventory'))throw Error('opponent popup exceeded observer projection or changed movement');
  const shield=currentView.entities.find(e=>e.category==='object'&&e.type.toLowerCase()==='small shield');
  if(!shield)throw Error('Small Shield evidence missing');
  const shieldRow=__element('entities').children.find(e=>e.dataset.handle===shield.handle);
  if(!shieldRow||shieldRow.textContent.includes('Small Shield · Small Shield'))throw Error('default duplicate name/type label remains');
  before=movementCount();await c.listeners.click({clientX:mapView.toX(shield.position_meters.x),clientY:mapView.toY(shield.position_meters.y)});
  if(movementCount()!==before||!__text(__element('dialogBody')).includes('Weight: Unavailable from observer evidence'))throw Error('Object popup did not preserve movement/authority boundary');
  const daggers=currentView.entities.filter(e=>e.category==='object'&&e.type==='Dagger');
  if(daggers.length<2||daggers[0].handle===daggers[1].handle)throw Error('duplicate-type Objects lost separate handles');
  before=movementCount();await __element('entities').children.find(e=>e.dataset.handle===daggers[0].handle).listeners.click();
  if(movementCount()!==before)throw Error('Entity list inspection changed destination');
  await __element('entities').children.find(e=>e.dataset.handle===daggers[1].handle).listeners.click();
  if(currentView.selected_entity.handle!==daggers[1].handle)throw Error('second same-type Object was not independently selectable');
  const initialObject=daggers[0];
  if(!initialObject)throw Error('generated object was not visible on the map');
  before=movementCount();await c.listeners.click({clientX:mapView.toX(initialObject.position_meters.x),clientY:mapView.toY(initialObject.position_meters.y)});
  if(movementCount()!==before)throw Error('Object inspection changed destination');
  let pickupEntry=currentView.action_catalog.entries.find(e=>e.name==='Pick up');
  if(pickupEntry.status!=='unavailable'||!pickupEntry.reason.includes('same hex'))throw Error('remote Object incorrectly enabled Pick up');
  let input=__find(__element('dialogBody'),'entityName');input.value='Renamed Dagger';
  await __find(__element('dialogBody'),'renameEntity').listeners.click();
  if(!__text(__element('dialogBody')).includes('Renamed Dagger')||!__text(__element('dialogBody')).includes('Type: Dagger'))throw Error('renamed popup lost distinct native type');
  const m=currentView.map,cell=__targetCell;
  const minX=0,maxX=m.origin_offset_meters[0]+(m.width_cells-1)*m.column_step_meters+m.hex_vertex_offsets_meters[0][0];
  const minY=0,maxY=m.height_cells*m.row_step_meters+(m.width_cells>1?m.odd_column_offset_meters:0);
  const scale=Math.min((c.clientWidth-24)/(maxX-minX),(c.clientHeight-24)/(maxY-minY));
  const ox=(c.clientWidth-(maxX-minX)*scale)/2,oy=(c.clientHeight-(maxY-minY)*scale)/2;
  const cx=m.origin_offset_meters[0]+cell.column*m.column_step_meters;
  const cy=m.origin_offset_meters[1]+cell.row*m.row_step_meters+(cell.column%2)*m.odd_column_offset_meters;
  await c.listeners.click({clientX:ox+(cx-minX)*scale+24,clientY:c.clientHeight-oy-(cy-minY)*scale});
  __element('rate').value='walk';await __element('rate').listeners.change();
  __element('rate').value='sprint';const optionRequest=__element('rate').listeners.change();
  const advanceRequest=__element('advance').onclick();await Promise.all([optionRequest,advanceRequest]);
  const visibleObject=__element('entities').children.find(e=>e.textContent.includes('Renamed Dagger'));
  if(!visibleObject)throw Error('renamed object disappeared after movement');
  await visibleObject.listeners.click();
  if(__find(__element('dialogBody'),'pickup').disabled)throw Error('same-hex object was not pickup-eligible after arrival');
  __element('characterButton').listeners.click({currentTarget:__element('characterButton')});
  if(__find(__element('dialogBody'),'actionPickup').disabled)throw Error('selector disagrees with same-hex Object popup eligibility');
  await __find(__element('dialogBody'),'actionPickup').listeners.click();
  if(!__find(__element('dialogBody'),'actionPickup').disabled)throw Error('pending native Pick up was not disabled');
  await __element('advance').onclick();
  if(!__find(__element('dialogBody'),'actionPickup').disabled)throw Error('Pick up stayed available after acquisition');
  const carried=__element('entities').children.find(e=>e.textContent.includes('Renamed Dagger'));
  if(!carried)throw Error('carried display name was not retained');
  __element('characterButton').listeners.click({currentTarget:__element('characterButton')});
  body=__text(__element('dialogBody'));
  if(!body.includes('Renamed Dagger')||!body.includes('carried; not readied')||!body.includes('Represented carried weight'))throw Error('committed inventory did not refresh in character popup');
  const playerSummary=body;
  const inventoryButton=__findHandle(__element('dialogBody'),initialObject.handle);
  if(!inventoryButton)throw Error('carried inventory item is not inspectable');
  await inventoryButton.listeners.click();
  body=__text(__element('dialogBody'));
  if(!body.includes('State: carried')||!body.includes('Renamed Dagger'))throw Error('carried Object popup did not reflect committed state');
  await __element('dialogClose').listeners.click();
  if(dialog.open||!__element('characterButton').focused)throw Error('popup close or focus restoration failed');
  globalThis.__result=JSON.stringify({calls:__calls,plan:__lastPlan,time:currentView.time_seconds,
    status:__element('movementStatus').textContent,error:__element('error').textContent,
    entityDetails:body,pickupStatus:'Pick up accepted',renameStatus:'renamed',finalEntity:currentView.selected_entity,
    characterSummary:playerSummary,characterInventory:currentView.character.inventory.items.map(item=>`${item.name} · ${item.status}`),
    entityLabels:__element('entities').children.map(e=>e.textContent),actionCatalog:currentView.action_catalog});
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
