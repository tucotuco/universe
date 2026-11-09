import Foundation
import JavaScriptCore

guard CommandLine.arguments.count == 5 || CommandLine.arguments.count == 6 else {
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
let movementRefusal = CommandLine.arguments.count == 6 ? read(CommandLine.arguments[5]) : "null"
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
var document={getElementById:__element,createElement(tag){return {tagName:tag,id:'',value:'',maxLength:0,type:'',className:'',textContent:'',dataset:Object.create(null),listeners:Object.create(null),children:[],appendChild(e){this.children.push(e);if(this.tagName==='select'&&this.children.length===1)this.value=e.value},append(...items){this.children.push(...items)},replaceChildren(){this.children=[]},addEventListener(name,fn){this.listeners[name]=fn},setAttribute(name,value){this[name]=value},focus(){this.focused=true}}}};
function __find(root,id){if(root.id===id)return root;for(const child of root.children||[]){const found=__find(child,id);if(found)return found}return null}
function __findHandle(root,handle){if(root.dataset&&root.dataset.handle===handle)return root;for(const child of root.children||[]){const found=__findHandle(child,handle);if(found)return found}return null}
function __text(root){return [root.textContent||'',...(root.children||[]).map(__text)].join(' ')}
var window={devicePixelRatio:1,listeners:Object.create(null),addEventListener:function(name,fn){this.listeners[name]=fn}};
var __serverState={state:'empty'};
var __initialView=__INITIAL_VIEW__;
var __targetCell=__TARGET_CELL__;
var __pickedUpView=__PICKED_UP_VIEW__;
var __movementRefusal=__MOVEMENT_REFUSAL__;
var __movementRefusalUsed=false;
var __enableMovementRefusal=false;
var __enableDrawableDraw=false;
var __calls=[];
var __lastPlan=null;
function __refreshActionCatalog(){
  const entries=__serverState.action_catalog&&__serverState.action_catalog.entries||[];
  const run=entries.find(e=>e.name==='Run');
  if(run&&run.status!=='not_implemented'){run.status=__serverState.run_available?'available':'unavailable';run.reason=__serverState.run_available?'The native target-free Run Choice can activate this Arena.':'Run is only accepted as the first player Action; this Encounter is already activated.'}
  const pickup=entries.find(e=>e.name==='Pick up');
  if(pickup){const target=__serverState.selected_entity;pickup.target=target?{handle:target.handle,name:target.name,type:target.type,present_state:target.present_state}:null;if(__serverState.pickup_action&&__serverState.pickup_action.status==='executing'){pickup.status='unavailable';pickup.reason='A native Pick up Action is already resolving.'}else if(!target||target.category!=='object'||target.present_state!=='ground'){pickup.status='unavailable';pickup.reason='Select a currently perceived ground Object first.'}else if(!__serverState.run_available&&target.pickup_available){pickup.status='available';pickup.reason='Native one-second Pick up is currently available for this Object.'}else{pickup.status='unavailable';pickup.reason=target.pickup_unavailable_reason||'Move into the same hex as this Object before choosing Pick up.'}}
  const ready=entries.find(e=>e.name.toLowerCase()==='ready weapon');if(ready){const target=__serverState.selected_entity;ready.target=target?{handle:target.handle,name:target.name,type:target.type,present_state:target.present_state}:null;if(__enableDrawableDraw&&target&&target.present_state==='carried'){ready.hands=['right hand'];ready.status='available';ready.display_name='Draw (2 s)';ready.reason='Test-authored worn sheath and free right hand; native ordinary drawing takes 2 seconds.'}else{ready.hands=[];ready.status='unavailable';ready.reason=target&&target.present_state==='carried'?'The carried Dagger has no authored drawable source location. Ground Pick up does not designate a sheath or hand; retrieval time is undetermined. Ordinary drawing is 2 seconds; post-strike re-readying is separate.':'Select a currently perceived, carried Weapon first.'}}
}
function __response(){return {ok:true,json:()=>Promise.resolve(JSON.parse(JSON.stringify(__serverState)))}}
function __clickMap(clientX,clientY){
  if(__element('entityDialog').open)return Promise.resolve(false);
  const listener=__element('map').listeners.click;
  if(typeof listener!=='function')throw Error('shipped canvas click listener was not initialized');
  return Promise.resolve(listener({clientX,clientY})).then(()=>true);
}
function fetch(path,options={}){
  const body=options.body===undefined?null:JSON.parse(options.body);
  __calls.push({path,method:options.method||'GET',body,headers:options.headers||{}});
  if(path==='/api/generated/advance'&&__enableMovementRefusal&&__movementRefusal&&!__movementRefusalUsed){
    __movementRefusalUsed=true;
    return Promise.resolve({ok:false,json:()=>Promise.resolve(__movementRefusal)});
  }
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
    }else if(__serverState.ready_weapon_action&&__serverState.ready_weapon_action.status==='executing'){
      __serverState.ready_weapon_action.seconds_remaining-=1;
      if(__serverState.ready_weapon_action.seconds_remaining===0){__serverState.ready_weapon_action={name:'Draw',status:'completed',outcome:'success',duration_seconds:2,seconds_remaining:0};if(__serverState.character&&__serverState.character.inventory.items.length)__serverState.character.inventory.items[0].status='readied in right hand';}
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
  } else if(path==='/api/generated/ready-weapon'){
    __serverState.ready_weapon_action={name:'Draw',status:'executing',outcome:null,duration_seconds:2,seconds_remaining:2};
    __serverState.advance_available=true;__refreshActionCatalog();
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
    .replacingOccurrences(of: "__MOVEMENT_REFUSAL__", with: movementRefusal)
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
  await __element('dialogClose').listeners.click();
  await __element('advance').onclick();
  if(currentView.time_seconds!==1||!currentView.player_action||currentView.player_action.status!=='completed')throw Error('Run did not resolve through native one-second advancement');
  __element('rate').value='sprint';await __element('rate').listeners.change();
  const movementCount=()=>__calls.filter(call=>call.path==='/api/generated/destination').length;
  __element('characterButton').listeners.click({currentTarget:__element('characterButton')});
  let before=movementCount(),p=currentView.player.position_meters;
  if(await __clickMap(mapView.toX(p.x),mapView.toY(p.y)))throw Error('open Character modal allowed a map click');
  if(movementCount()!==before||__calls.some(call=>call.path==='/api/generated/trace'&&call.body.event==='canvas_click_received'))throw Error('modal-blocked click reached the canvas handler');
  await __element('dialogClose').listeners.click();
  await __clickMap(mapView.toX(p.x),mapView.toY(p.y));
  if(movementCount()!==before||__element('dialogTitle').textContent!=='Your Being — Character')throw Error('player marker changed destination or missed popup');
  await __element('dialogClose').listeners.click();
  const opponent=currentView.entities.find(e=>e.category==='being');
  if(!opponent)throw Error('opponent evidence missing');
  before=movementCount();await __clickMap(mapView.toX(opponent.position_meters.x),mapView.toY(opponent.position_meters.y));
  body=__text(__element('dialogBody'));
  if(movementCount()!==before||!body.includes(opponent.type)||!body.includes(opponent.present_state)||body.includes('Total native XP')||body.includes('inventory'))throw Error('opponent popup exceeded observer projection or changed movement');
  await __element('dialogClose').listeners.click();
  const shield=currentView.entities.find(e=>e.category==='object'&&e.type.toLowerCase()==='small shield');
  if(!shield)throw Error('Small Shield evidence missing');
  const shieldRow=__element('entities').children.find(e=>e.dataset.handle===shield.handle);
  if(!shieldRow||shieldRow.textContent.includes('Small Shield · Small Shield'))throw Error('default duplicate name/type label remains');
  before=movementCount();await __clickMap(mapView.toX(shield.position_meters.x),mapView.toY(shield.position_meters.y));
  if(movementCount()!==before||!__text(__element('dialogBody')).includes('Weight: Unavailable from observer evidence'))throw Error('Object popup did not preserve movement/authority boundary');
  await __element('dialogClose').listeners.click();
  const daggers=currentView.entities.filter(e=>e.category==='object'&&e.type==='Dagger');
  if(daggers.length<2||daggers[0].handle===daggers[1].handle)throw Error('duplicate-type Objects lost separate handles');
  before=movementCount();await __element('entities').children.find(e=>e.dataset.handle===daggers[0].handle).listeners.click();
  if(movementCount()!==before)throw Error('Entity list inspection changed destination');
  await __element('dialogClose').listeners.click();
  await __element('entities').children.find(e=>e.dataset.handle===daggers[1].handle).listeners.click();
  if(currentView.selected_entity.handle!==daggers[1].handle)throw Error('second same-type Object was not independently selectable');
  await __element('dialogClose').listeners.click();
  const initialObject=daggers[0];
  if(!initialObject)throw Error('generated object was not visible on the map');
  before=movementCount();await __clickMap(mapView.toX(initialObject.position_meters.x),mapView.toY(initialObject.position_meters.y));
  if(movementCount()!==before)throw Error('Object inspection changed destination');
  let pickupEntry=currentView.action_catalog.entries.find(e=>e.name==='Pick up');
  if(pickupEntry.status!=='unavailable'||!pickupEntry.reason.includes('same hex'))throw Error('remote Object incorrectly enabled Pick up');
  let input=__find(__element('dialogBody'),'entityName');input.value='Renamed Dagger';
  await __find(__element('dialogBody'),'renameEntity').listeners.click();
  if(!__text(__element('dialogBody')).includes('Renamed Dagger')||!__text(__element('dialogBody')).includes('Type: Dagger'))throw Error('renamed popup lost distinct native type');
  before=movementCount();
  const m=currentView.map,cell=__targetCell;
  const minX=0,maxX=m.origin_offset_meters[0]+(m.width_cells-1)*m.column_step_meters+m.hex_vertex_offsets_meters[0][0];
  const minY=0,maxY=m.height_cells*m.row_step_meters+(m.width_cells>1?m.odd_column_offset_meters:0);
  const scale=Math.min((c.clientWidth-24)/(maxX-minX),(c.clientHeight-24)/(maxY-minY));
  const ox=(c.clientWidth-(maxX-minX)*scale)/2,oy=(c.clientHeight-(maxY-minY)*scale)/2;
  const cx=m.origin_offset_meters[0]+cell.column*m.column_step_meters;
  const cy=m.origin_offset_meters[1]+cell.row*m.row_step_meters+(cell.column%2)*m.odd_column_offset_meters;
  if(await __clickMap(ox+(cx-minX)*scale+24,c.clientHeight-oy-(cy-minY)*scale))throw Error('Object modal allowed a destination click');
  if(movementCount()!==before)throw Error('click behind an open Object dialog changed destination');
  await __element('dialogClose').listeners.click();
  before=movementCount();await __clickMap(ox+(cx-minX)*scale+24,c.clientHeight-oy-(cy-minY)*scale);
  if(movementCount()!==before+1||!currentView.movement_plan)throw Error('blank hex click did not submit a destination plan');
  __element('rate').value='walk';await __element('rate').listeners.change();
  __element('rate').value='sprint';const optionRequest=__element('rate').listeners.change();
  const advanceRequest=__element('advance').onclick();await Promise.all([optionRequest,advanceRequest]);
  const visibleObject=__element('entities').children.find(e=>e.textContent.includes('Renamed Dagger'));
  if(!visibleObject)throw Error('renamed object disappeared after movement');
  await visibleObject.listeners.click();
  if(__find(__element('dialogBody'),'pickup').disabled)throw Error('same-hex object was not pickup-eligible after arrival');
  await __element('dialogClose').listeners.click();
  __element('characterButton').listeners.click({currentTarget:__element('characterButton')});
  if(__find(__element('dialogBody'),'actionPickup').disabled)throw Error('selector disagrees with same-hex Object popup eligibility');
  await __find(__element('dialogBody'),'actionPickup').listeners.click();
  if(!__find(__element('dialogBody'),'actionPickup').disabled)throw Error('pending native Pick up was not disabled');
  await __element('dialogClose').listeners.click();
  await __element('advance').onclick();
  if(!__find(__element('dialogBody'),'actionPickup').disabled)throw Error('Pick up stayed available after acquisition');
  const carried=__element('entities').children.find(e=>e.textContent.includes('Renamed Dagger'));
  if(!carried)throw Error('carried display name was not retained');
  __element('characterButton').listeners.click({currentTarget:__element('characterButton')});
  body=__text(__element('dialogBody'));
  if(!body.includes('Renamed Dagger')||!body.includes('carried; not readied')||!body.includes('Represented carried weight'))throw Error('committed inventory did not refresh in character popup');
  const readyButton=__find(__element('dialogBody'),'actionReadyWeapon'),readyHand=__find(__element('dialogBody'),'readyWeaponHand');
  if(!readyButton||!readyButton.disabled||readyHand)throw Error('unsupported Ready weapon Action was not disabled without drawable-location state');
  const readyReason=__find(__element('dialogBody'),'actionReadyWeapon').title;
  if(!readyReason.includes('drawable source location')||!readyReason.includes('Ground Pick up')||!readyReason.includes('2 seconds')||!readyReason.includes('post-strike re-readying'))throw Error('Ready weapon refusal did not distinguish the native timing rules: '+readyReason);
  if(__calls.some(call=>call.path==='/api/generated/ready-weapon'))throw Error('disabled Ready weapon submitted a request');
  const playerSummary=body,carriedInventory=currentView.character.inventory.items.map(item=>`${item.name} · ${item.status}`);
  // This is an explicitly test-authored browser fixture: the carried dagger is
  // given an owner-linked drawable sheath record and the Being a free hand.
  __enableDrawableDraw=true;__serverState.selected_entity=__serverState.entities.find(e=>e.handle===initialObject.handle);
  __refreshActionCatalog();show(__serverState);
  const drawEntry=currentView.action_catalog.entries.find(e=>e.name.toLowerCase()==='ready weapon');
  const drawButton=__find(__element('dialogBody'),'actionReadyWeapon'),drawHand=__find(__element('dialogBody'),'readyWeaponHand');
  if(drawEntry.status!=='available'||drawEntry.display_name!=='Draw (2 s)'||!drawButton||drawButton.disabled||!drawHand||drawHand.value!=='right hand')throw Error('explicit native Draw prerequisites did not reach the browser selector');
  await drawButton.listeners.click();
  if(!currentView.ready_weapon_action||currentView.ready_weapon_action.status!=='executing'||currentView.ready_weapon_action.seconds_remaining!==2)throw Error('browser Draw Choice did not show a pending two-second Action');
  if(!__calls.some(call=>call.path==='/api/generated/ready-weapon'&&call.body.handle===initialObject.handle&&call.body.hand==='right hand'))throw Error('browser did not submit the selected handle and free native hand');
  await __element('advance').onclick();
  if(currentView.ready_weapon_action.status!=='executing'||currentView.ready_weapon_action.seconds_remaining!==1||currentView.character.inventory.items[0].status!=='carried; not readied')throw Error('browser exposed Draw readiness before its second boundary');
  await __element('advance').onclick();
  if(currentView.ready_weapon_action.status!=='completed'||currentView.ready_weapon_action.outcome!=='success'||currentView.character.inventory.items[0].status!=='readied in right hand')throw Error('browser did not show atomic Draw completion at the second boundary');
  if(__calls.filter(call=>call.path==='/api/generated/advance').length<3)throw Error('browser Draw progression did not use native one-second Advance requests');
  const inventoryButton=__findHandle(__element('dialogBody'),initialObject.handle);
  if(!inventoryButton)throw Error('carried inventory item is not inspectable');
  await inventoryButton.listeners.click();
  body=__text(__element('dialogBody'));
  if(!body.includes('State: carried')||!body.includes('Renamed Dagger'))throw Error('carried Object popup did not reflect committed state');
  await __element('dialogClose').listeners.click();
  if(dialog.open||!__element('characterButton').focused)throw Error('popup close or focus restoration failed');
  const carriedEntity=currentView.selected_entity;
  const runCountBeforeMovement=__calls.filter(call=>call.path==='/api/generated/run').length;
  await __element('generate').onclick();
  const freshPosition=currentView.player.position_meters;
  const freshMap=currentView.map,destination=__targetCell;
  const freshMaxX=freshMap.origin_offset_meters[0]+(freshMap.width_cells-1)*freshMap.column_step_meters+freshMap.hex_vertex_offsets_meters[0][0];
  const freshMaxY=freshMap.height_cells*freshMap.row_step_meters+(freshMap.width_cells>1?freshMap.odd_column_offset_meters:0);
  const freshScale=Math.min((c.clientWidth-24)/(freshMaxX),(c.clientHeight-24)/(freshMaxY));
  const freshOx=(c.clientWidth-(freshMaxX*freshScale))/2,freshOy=(c.clientHeight-(freshMaxY*freshScale))/2;
  const destX=freshMap.origin_offset_meters[0]+destination.column*freshMap.column_step_meters;
  const destY=freshMap.origin_offset_meters[1]+destination.row*freshMap.row_step_meters+(destination.column%2)*freshMap.odd_column_offset_meters;
  __element('characterButton').listeners.click({currentTarget:__element('characterButton')});
  const freshActions=__find(__element('dialogBody'),'actionSelector');
  if(!freshActions)throw Error('Character Actions did not reopen after fresh Generate');
  freshActions.open=true;freshActions.listeners.toggle();
  await __element('dialogClose').listeners.click();
  const freshBefore=movementCount();
  __element('rate').value='walk';
  await __clickMap(freshOx+destX*freshScale+24,c.clientHeight-freshOy-destY*freshScale);
  if(movementCount()!==freshBefore+1||currentView.time_seconds!==0||currentView.player_action)throw Error('fresh movement selection scheduled an Action or failed to accept its plan');
  __element('facingPolicy').value='maintain';await __element('facingPolicy').listeners.change();
  __element('facingPolicy').value='turn';const finalFacingUpdate=__element('facingPolicy').listeners.change();
  __element('rate').value='sprint';const finalRateUpdate=__element('rate').listeners.change();
  await Promise.all([finalFacingUpdate,finalRateUpdate]);
  await __element('advance').onclick();
  if(currentView.time_seconds!==1||currentView.player.position_meters.x===freshPosition.x&&currentView.player.position_meters.y===freshPosition.y)throw Error('fresh destination did not advance to a displaced native position');
  if(__calls.filter(call=>call.path==='/api/generated/run').length!==runCountBeforeMovement)throw Error('movement activation submitted Run');
  if(__movementRefusal){
    const current=currentView.player.cell,cell=current.column===0&&current.row===0?{column:1,row:1}:{column:0,row:0};
    const x=currentView.map.origin_offset_meters[0]+cell.column*currentView.map.column_step_meters;
    const y=currentView.map.origin_offset_meters[1]+cell.row*currentView.map.row_step_meters+(cell.column%2)*currentView.map.odd_column_offset_meters;
    const beforeTime=currentView.time_seconds;
    __enableMovementRefusal=true;
    await __clickMap(mapView.toX(x),mapView.toY(y));
    await __element('advance').onclick();
    if(!__element('error').textContent.includes(__movementRefusal.movement_refusal.message))throw Error('structured movement refusal was not shown in the shipped UI');
    if(__element('error').dataset.refusalCategory!==__movementRefusal.movement_refusal.category||currentView.time_seconds!==beforeTime||!currentView.movement_plan)throw Error('UI refusal lost its category or authoritative plan');
  }
  globalThis.__result=JSON.stringify({calls:__calls,plan:__lastPlan,time:currentView.time_seconds,
    freshMovement:{position:currentView.player.position_meters,start:freshPosition,
      time:currentView.time_seconds,playerAction:currentView.player_action,
      runCountBefore:runCountBeforeMovement,
      runCount:__calls.filter(call=>call.path==='/api/generated/run').length},
    status:__element('movementStatus').textContent,error:__element('error').textContent,
    refusalCategory:__element('error').dataset.refusalCategory||'',
    entityDetails:body,pickupStatus:'Pick up accepted',renameStatus:'renamed',finalEntity:carriedEntity,
    characterSummary:playerSummary,characterInventory:carriedInventory,
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
