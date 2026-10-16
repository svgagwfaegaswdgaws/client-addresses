'use strict';
const $ = (selector) => document.querySelector(selector);
const state = {tab:'addresses', data:{countries:[],regions:[],cities:[],addresses:[]}, loaded:false, editing:null, deleting:null};
const configs = {
 addresses:{title:'Список адресов',description:'Клиенты, города и контактные адреса',add:'Добавить адрес',edit:'Изменить адрес',empty:'Адресов пока нет',help:'Добавьте первый адрес или загрузите учебные примеры.',search:'Найти клиента или адрес'},
 cities:{title:'Города',description:'Города и их принадлежность к регионам',add:'Добавить город',edit:'Изменить город',empty:'Городов пока нет',help:'Сначала добавьте страну и регион.',search:'Найти город'},
 regions:{title:'Регионы',description:'Области и регионы по странам',add:'Добавить регион',edit:'Изменить регион',empty:'Регионов пока нет',help:'Сначала добавьте страну.',search:'Найти регион'},
 countries:{title:'Страны',description:'Полные и краткие названия стран',add:'Добавить страну',edit:'Изменить страну',empty:'Стран пока нет',help:'Добавьте страну, чтобы начать работу.',search:'Найти страну'}
};
const editIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="m16 3 5 5M4 15 16 3a2 2 0 0 1 3 0l2 2a2 2 0 0 1 0 3L9 20l-6 1z"/></svg>';
const deleteIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/></svg>';
const find = (table,id) => state.data[table].find(row=>row.ID===id);
const node = (tag,text,className) => {const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;};
function locationOf(row,tab=state.tab){
 const city=tab==='addresses'?find('cities',row.CityID):tab==='cities'?row:null;
 const region=city?find('regions',city.RegionID):tab==='regions'?row:null;
 const country=region?find('countries',region.CountryID):tab==='countries'?row:null;
 return {city,region,country};
}
function setStatus(online){const status=$('#status');status.className='status '+(online?'online':'offline');status.querySelector('span').textContent=online?'Сервер доступен':'Нет соединения';}
async function request(path,method='GET',data){
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),12000);
 try{
  const options={method,signal:controller.signal,cache:'no-store',headers:{}};
  if(data!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}
  const response=await fetch('/api/'+path,options);
  if(!(response.headers.get('content-type')||'').includes('application/json'))throw new Error('Сервер вернул неверный ответ. Проверьте адрес подключения.');
  const payload=await response.json();setStatus(true);
  if(!response.ok)throw new Error(payload.error||'Не удалось выполнить запрос.');
  return payload;
 }catch(error){
  if(error.name==='AbortError'||error instanceof TypeError){setStatus(false);throw new Error('Не удалось подключиться к серверу. Проверьте интернет и повторите попытку.');}
  throw error;
 }finally{clearTimeout(timer);}
}
async function load(){
 $('#refresh').disabled=true;$('#add').disabled=!state.loaded;
 try{state.data=await request('snapshot');state.loaded=true;$('#error').hidden=true;render();return true;}
 catch(error){$('#error span').textContent=error.message;$('#error').hidden=false;if(!state.loaded){$('#content').replaceChildren(node('div','Данные недоступны. Нажмите «Повторить».','empty'));}return false;}
 finally{$('#refresh').disabled=false;$('#add').disabled=!state.loaded;}
}
let toastTimer;
function toast(text){clearTimeout(toastTimer);$('#toast').textContent=text;$('#toast').hidden=false;toastTimer=setTimeout(()=>$('#toast').hidden=true,3500);}
function cell(text,sub,className){const td=node('td',undefined,className);td.append(node('strong',text));if(sub)td.append(node('small',sub));return td;}
function render(){
 const cfg=configs[state.tab];$('#list-title').textContent=cfg.title;$('#list-description').textContent=cfg.description;$('#add').textContent='+ '+cfg.add;$('#search').placeholder=cfg.search;
 document.querySelectorAll('[data-tab]').forEach(button=>{const active=button.dataset.tab===state.tab;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');button.querySelector('span').textContent=state.data[button.dataset.tab].length;});
 const query=$('#search').value.trim().toLocaleLowerCase('ru');
 const rows=state.data[state.tab].filter(row=>{const loc=locationOf(row);return [...Object.values(row),loc.city?.City,loc.region?.Region,loc.country?.CountryFull,loc.country?.CountryShort].filter(v=>v!==undefined).join(' ').toLocaleLowerCase('ru').includes(query);});
 $('#shown').textContent=`Показано: ${rows.length} из ${state.data[state.tab].length}`;
 $('#demo').hidden=Object.values(state.data).some(list=>list.length>0);
 if(!rows.length){const empty=node('div',undefined,'empty');empty.append(node('div','⌖','empty-icon'),node('h3',query?'Ничего не найдено':cfg.empty),node('p',query?'Попробуйте изменить поисковый запрос.':cfg.help));$('#content').replaceChildren(empty);return;}
 const table=node('table');const head=node('thead');const header=node('tr');
 const columns=state.tab==='addresses'?['Клиент','Адрес','Регион / страна','']:state.tab==='cities'?['Город','Регион','Страна','']:state.tab==='regions'?['Регион','Страна','']:['Страна','Краткое название',''];
 columns.forEach((title,i)=>{const th=node('th',title);th.scope='col';if(i===columns.length-1){th.className='actions';th.append(node('span','Действия'));}if(state.tab==='addresses'&&i===2)th.className='region-col';header.append(th);});head.append(header);table.append(head);
 const tbody=node('tbody');
 rows.forEach(row=>{
  const tr=node('tr');const {city,region,country}=locationOf(row);const label=row.Person||row.City||row.Region||row.CountryFull;
  if(state.tab==='addresses'){tr.append(cell(row.Person,'ID '+row.ID),cell(`${city?.City||'—'}, ул. ${row.Street}, ${row.Building}`,row.Office?'офис '+row.Office:''),cell(region?.Region||'—',country?.CountryShort,'region-col'));}
  else if(state.tab==='cities'){tr.append(cell(row.City),cell(region?.Region||'—'),cell(country?.CountryShort||'—'));}
  else if(state.tab==='regions'){tr.append(cell(row.Region),cell(country?.CountryShort||'—'));}
  else{tr.append(cell(row.CountryFull));const td=node('td');td.append(node('span',row.CountryShort,'badge'));tr.append(td);}
  const actions=node('td',undefined,'actions');const edit=node('button',undefined,'row-action');edit.innerHTML=editIcon;edit.type='button';edit.title='Изменить';edit.setAttribute('aria-label','Изменить: '+label);edit.onclick=()=>openEditor(row);
  const del=node('button',undefined,'row-action delete');del.innerHTML=deleteIcon;del.type='button';del.title='Удалить';del.setAttribute('aria-label','Удалить: '+label);del.onclick=()=>openDelete(row);actions.append(edit,del);tr.append(actions);tbody.append(tr);
 });table.append(tbody);const wrap=node('div',undefined,'table-wrap');wrap.append(table);$('#content').replaceChildren(wrap);
}
function field(name,label,type='text',value='',max=120){
 const wrap=node('div',undefined,'field');const id='field-'+name;const labelNode=node('label',label);labelNode.htmlFor=id;const input=node(type==='select'?'select':'input');input.id=id;input.name=name;if(type!=='select'){input.type='text';input.maxLength=max;input.value=value??'';}input.required=name!=='Office';wrap.append(labelNode,input);$('#fields').append(wrap);return input;
}
function choices(select,rows,key,selected){select.replaceChildren(new Option(rows.length?'Выберите…':'Нет записей — добавьте в справочнике',''));rows.slice().sort((a,b)=>a[key].localeCompare(b[key],'ru')).forEach(row=>select.add(new Option(row[key],row.ID)));select.value=selected?String(selected):'';select.disabled=!rows.length;}
function openEditor(row=null){
 state.editing={tab:state.tab,id:row?.ID};const cfg=configs[state.tab];$('#editor-title').textContent=row?cfg.edit:cfg.add;$('#editor-label').textContent=row?'РЕДАКТИРОВАНИЕ':'НОВАЯ ЗАПИСЬ';$('#fields').replaceChildren();$('#form-error').hidden=true;
 if(state.tab==='countries'){field('CountryFull','Полное название','text',row?.CountryFull,120);field('CountryShort','Краткое название','text',row?.CountryShort,20);}
 else{
  const loc=row?locationOf(row):{};
  if(state.tab==='addresses')field('Person','Клиент','text',row?.Person,160);
  const country=field(state.tab==='regions'?'CountryID':'country','Страна','select');choices(country,state.data.countries,'CountryFull',loc.country?.ID);
  if(state.tab==='regions')field('Region','Название региона','text',row?.Region,120);
  else{
   const region=field(state.tab==='cities'?'RegionID':'region','Регион','select');
   const updateRegion=selected=>choices(region,state.data.regions.filter(r=>r.CountryID===Number(country.value)),'Region',selected);updateRegion(loc.region?.ID);
   if(state.tab==='cities'){field('City','Название города','text',row?.City,120);country.onchange=()=>updateRegion();}
   else{
    const city=field('CityID','Город','select');const updateCity=selected=>choices(city,state.data.cities.filter(c=>c.RegionID===Number(region.value)),'City',selected);updateCity(row?.CityID);
    country.onchange=()=>{updateRegion();updateCity();};region.onchange=()=>updateCity();field('Street','Улица','text',row?.Street,160);
    const building=field('Building','Дом / строение','text',row?.Building,30);const office=field('Office','Офис (необязательно)','text',row?.Office,30);const fieldRow=node('div',undefined,'field-row');building.parentNode.before(fieldRow);fieldRow.append(building.parentNode,office.parentNode);
   }
  }
 }
 $('#editor').showModal();
}
$('#form').onsubmit=async event=>{
 event.preventDefault();if(!state.editing)return;$('#save').disabled=true;$('#form-error').hidden=true;
 const payload=Object.fromEntries(new FormData($('#form')));delete payload.country;delete payload.region;
 for(const key of ['CountryID','RegionID','CityID']){if(key in payload)payload[key]=Number(payload[key]);}
 try{const {tab,id}=state.editing;await request(tab+(id?'/'+id:''),id?'PUT':'POST',payload);$('#editor').close();toast(id?'Изменения сохранены':'Запись добавлена');await load();}
 catch(error){$('#form-error').textContent=error.message;$('#form-error').hidden=false;}
 finally{$('#save').disabled=false;}
};
function openDelete(row){state.deleting={tab:state.tab,id:row.ID};$('#delete-description').textContent=`«${row.Person||row.City||row.Region||row.CountryFull}» будет удалено. Это действие нельзя отменить.`;$('#delete-error').hidden=true;$('#delete-dialog').showModal();}
$('#delete-form').onsubmit=async event=>{event.preventDefault();if(!state.deleting)return;$('#delete-confirm').disabled=true;try{await request(state.deleting.tab+'/'+state.deleting.id,'DELETE');$('#delete-dialog').close();toast('Запись удалена');await load();}catch(error){$('#delete-error').textContent=error.message;$('#delete-error').hidden=false;}finally{$('#delete-confirm').disabled=false;}};
$('#delete-cancel').onclick=()=>$('#delete-dialog').close();$('#close').onclick=$('#cancel').onclick=()=>$('#editor').close();
document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>{state.tab=button.dataset.tab;$('#search').value='';if(state.loaded)render();});
$('#search').oninput=()=>{if(state.loaded)render();};$('#add').onclick=()=>openEditor();$('#refresh').onclick=$('#retry').onclick=load;
$('#demo').onclick=async()=>{$('#demo').disabled=true;try{await request('demo','POST',{});toast('Учебные примеры добавлены');await load();}catch(error){$('#error span').textContent=error.message;$('#error').hidden=false;}finally{$('#demo').disabled=false;}};
load();
