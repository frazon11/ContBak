const I18N = {
  en: {
    backup_running:'Backup running', preparing_backup:'Preparing backup…', backup_running_dots:'Backup running…', back_up_now:'Back up now', try_again:'Try again', job_status_failed:'Could not read job status.', backup_completed:'Backup completed.', backup_starting:'Starting backup…', sending_request:'Sending request…', backup_started:'Backup started.', backup_start_failed:'Could not start backup.', select_backup:'Please select at least one backup.', import_running:'Importing…', upload_verifying:'Uploading and verifying file…', import_failed:'Import failed', import_success:'Backup imported successfully.', upload_import:'Upload & import', cards:'Cards', details:'Details', view:'View', image:'Image', stack:'Stack', service:'Service', mounts:'Mounts', status:'Status', schedule:'Schedule', actions:'Actions'
  },
  de: {
    backup_running:'Backup läuft', preparing_backup:'Backup wird vorbereitet …', backup_running_dots:'Backup läuft …', back_up_now:'Jetzt sichern', try_again:'Erneut versuchen', job_status_failed:'Jobstatus konnte nicht gelesen werden.', backup_completed:'Backup abgeschlossen.', backup_starting:'Backup startet …', sending_request:'Anfrage wird gesendet …', backup_started:'Backup wurde gestartet.', backup_start_failed:'Backup konnte nicht gestartet werden.', select_backup:'Bitte mindestens ein Backup auswählen.', import_running:'Import läuft …', upload_verifying:'Datei wird hochgeladen und geprüft …', import_failed:'Import fehlgeschlagen', import_success:'Backup erfolgreich importiert.', upload_import:'Upload & Import', cards:'Karten', details:'Details', view:'Ansicht', image:'Image', stack:'Stack', service:'Dienst', mounts:'Mounts', status:'Status', schedule:'Zeitplan', actions:'Aktionen'
  }
};

let currentLanguage = localStorage.getItem('contbak-language') || 'en';
function t(key){ return (I18N[currentLanguage] && I18N[currentLanguage][key]) || I18N.en[key] || key; }

const STATIC_DE = {
  'Dashboard':'Übersicht','Schedules':'Zeitpläne','Logs':'Protokoll','Docker connection active':'Docker-Verbindung aktiv','Docker Backup':'Docker-Sicherung','Back up all':'Alle sichern','Container status':'Containerstatus','Current Docker environment status':'Aktueller Zustand der Docker-Umgebung','Show all':'Alle anzeigen','Latest backups':'Letzte Sicherungen','Most recent backup sets':'Neueste Backup-Sätze','Back up individual services and manage schedules':'Einzelne Dienste sichern und Zeitpläne verwalten','Show mounts':'Mounts anzeigen','Stop container':'Container stoppen','Back up now':'Jetzt sichern','Save schedule':'Zeitplan speichern','Restore, download, export and import':'Wiederherstellen, herunterladen, exportieren und importieren','Import backup':'Backup importieren','Rename duplicate':'Duplikat umbenennen','Skip duplicate':'Duplikat überspringen','Replace duplicate':'Duplikat ersetzen','Upload & import':'Upload & Import','Export selected':'Ausgewählte exportieren','Date/time':'Zeitpunkt','Size':'Größe','Path':'Pfad','Action':'Aktion','Automatic daily backups':'Automatische tägliche Sicherungen','Execution':'Ausführung','Delete':'Löschen','Results of recent backup and restore operations':'Ergebnisse der letzten Backup- und Restore-Vorgänge','Message':'Meldung','Search containers…':'Container suchen …','Language':'Sprache'
};

function applyLanguage(lang){
  currentLanguage=lang;
  localStorage.setItem('contbak-language',lang);
  document.documentElement.lang=lang;
  document.querySelectorAll('[data-en-text]').forEach(el=>{el.textContent=lang==='de'?(STATIC_DE[el.dataset.enText]||el.dataset.enText):el.dataset.enText});
  const search=document.getElementById('container-search');
  if(search) search.placeholder=lang==='de'?'Container suchen …':'Search containers…';
  refreshViewToggleLabels();
  rebuildContainerDetails();
}

function markTranslatable(){
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  const nodes=[];
  while(walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(node=>{
    const value=node.nodeValue.trim();
    if(value && STATIC_DE[value]){
      const span=document.createElement('span');
      span.dataset.enText=value;
      span.textContent=value;
      node.parentNode.replaceChild(span,node);
    }
  });
}

function escapeHtml(value){
  const div=document.createElement('div');
  div.textContent=String(value ?? '');
  return div.innerHTML;
}

function showToast(message,type='info'){
  let host=document.querySelector('.toast-host');
  if(!host){host=document.createElement('div');host.className='toast-host';document.body.appendChild(host)}
  const item=document.createElement('div');
  item.className=`toast toast-${type}`;
  item.textContent=message;
  host.appendChild(item);
  requestAnimationFrame(()=>item.classList.add('show'));
  setTimeout(()=>{item.classList.remove('show');setTimeout(()=>item.remove(),250)},5000);
}

function injectContainerViewStyles(){
  if(document.getElementById('container-view-styles')) return;
  const style=document.createElement('style');
  style.id='container-view-styles';
  style.textContent=`
    .container-toolbar{display:flex;align-items:center;justify-content:flex-end;gap:10px;flex-wrap:wrap}
    .view-switch{display:inline-flex;padding:3px;border:1px solid var(--line);border-radius:10px;background:var(--surface)}
    .view-switch button{border:0;background:transparent;color:var(--muted);padding:7px 11px;border-radius:7px;font:inherit;font-size:12px;font-weight:700;cursor:pointer}
    .view-switch button.active{background:#26344c;color:#fff}
    .container-details-view{display:none}
    .container-details-view.active{display:block}
    .container-grid.view-hidden{display:none}
    .container-detail-table{min-width:1080px}
    .container-detail-table td{vertical-align:middle}
    .container-detail-name{display:flex;align-items:center;gap:10px;min-width:180px}
    .container-detail-name .service-icon{width:32px;height:32px}
    .container-image-cell{max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--muted)}
    .detail-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;min-width:330px}
    .detail-actions .backup-form{display:flex;align-items:center;gap:8px}
    .detail-actions .schedule-form{display:flex;align-items:center;gap:7px}
    .detail-actions .schedule-form input{width:105px}
    .detail-actions .btn{white-space:nowrap}
    .detail-progress-row td{padding-top:0;background:rgba(255,255,255,.01)}
    .detail-progress-row .backup-progress{max-width:760px;margin-left:auto}
    @media(max-width:760px){.container-toolbar{width:100%;justify-content:space-between}.view-switch{margin-left:auto}}
  `;
  document.head.appendChild(style);
}

function cardData(card){
  const title=card.querySelector('h3')?.textContent.trim() || '';
  const image=card.querySelector('.card-topline p')?.textContent.trim() || '';
  const status=card.querySelector('.badge')?.textContent.trim() || '';
  const values=[...card.querySelectorAll('.meta-grid > div')].map(item=>({label:item.querySelector('span')?.textContent.trim()||'',value:item.querySelector('strong')?.textContent.trim()||''}));
  const get=(label)=>values.find(item=>item.label.toLowerCase()===label)?.value || '–';
  const form=card.querySelector('.backup-form');
  const schedule=card.querySelector('.schedule-form');
  return {
    card,name:title,image,status,
    stack:get('stack'),service:get('service'),mounts:get('mounts'),id:get('id'),
    containerId:form?.action.split('/').filter(Boolean).pop()||'',
    stopChecked:form?.querySelector('input[name="stop"]')?.checked ?? false,
    scheduleAction:schedule?.action||'',
    scheduleTime:schedule?.querySelector('input[type="time"]')?.value||'03:00',
    search:card.dataset.search||''
  };
}

function refreshViewToggleLabels(){
  document.querySelectorAll('[data-container-view="cards"]').forEach(button=>button.textContent=t('cards'));
  document.querySelectorAll('[data-container-view="details"]').forEach(button=>button.textContent=t('details'));
}

function ensureContainerViewToggle(){
  const heading=document.querySelector('#tab-containers .section-heading');
  const search=document.getElementById('container-search');
  if(!heading || !search || document.getElementById('container-view-switch')) return;
  const toolbar=document.createElement('div');
  toolbar.className='container-toolbar';
  search.parentNode.insertBefore(toolbar,search);
  toolbar.appendChild(search);
  const toggle=document.createElement('div');
  toggle.id='container-view-switch';
  toggle.className='view-switch';
  toggle.setAttribute('aria-label','Container view');
  toggle.innerHTML='<button type="button" data-container-view="cards"></button><button type="button" data-container-view="details"></button>';
  toolbar.appendChild(toggle);
  refreshViewToggleLabels();
  toggle.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>setContainerView(button.dataset.containerView)));
}

function rebuildContainerDetails(){
  const grid=document.getElementById('container-grid');
  if(!grid) return;
  let view=document.getElementById('container-details-view');
  if(!view){view=document.createElement('div');view.id='container-details-view';view.className='container-details-view table-card';grid.insertAdjacentElement('afterend',view)}
  const rows=[...grid.querySelectorAll('.container-card')].map(cardData);
  view.innerHTML=`<div class="table-wrap"><table class="container-detail-table"><thead><tr>
    <th>Container</th><th>${t('image')}</th><th>${t('status')}</th><th>${t('stack')}</th><th>${t('service')}</th><th>${t('mounts')}</th><th>ID</th><th class="right">${t('actions')}</th>
  </tr></thead><tbody>${rows.map((item,index)=>`
    <tr class="container-detail-row" data-search="${escapeHtml(item.search)}" data-card-index="${index}">
      <td><div class="container-detail-name"><div class="service-icon">${escapeHtml(item.name.slice(0,2).toUpperCase())}</div><strong>${escapeHtml(item.name)}</strong></div></td>
      <td class="container-image-cell" title="${escapeHtml(item.image)}">${escapeHtml(item.image)}</td>
      <td><span class="badge badge-${escapeHtml(item.status.toLowerCase())}">${escapeHtml(item.status)}</span></td>
      <td>${escapeHtml(item.stack)}</td><td>${escapeHtml(item.service)}</td><td><span class="pill">${escapeHtml(item.mounts)}</span></td><td><code>${escapeHtml(item.id)}</code></td>
      <td class="right"><div class="detail-actions">
        <form method="post" action="/backup/${encodeURIComponent(item.containerId)}" class="backup-form detail-backup-form">
          <label class="switch-row"><input type="checkbox" name="stop" ${item.stopChecked?'checked':''}><span>${currentLanguage==='de'?'Stoppen':'Stop'}</span></label>
          <button class="btn btn-primary btn-small" type="submit">${t('back_up_now')}</button>
        </form>
        <form method="post" action="${escapeHtml(item.scheduleAction)}" class="schedule-form detail-schedule-form">
          <input type="time" name="time" value="${escapeHtml(item.scheduleTime)}" required>
          <button class="btn btn-secondary btn-small" type="submit">${currentLanguage==='de'?'Speichern':'Save'}</button>
        </form>
      </div></td>
    </tr><tr class="detail-progress-row hidden"><td colspan="8"></td></tr>`).join('')}</tbody></table></div>`;
  bindBackupForms(view);
  filterContainers();
}

function setContainerView(viewName){
  const view=viewName==='details'?'details':'cards';
  localStorage.setItem('contbak-container-view',view);
  const grid=document.getElementById('container-grid');
  const details=document.getElementById('container-details-view');
  if(grid) grid.classList.toggle('view-hidden',view==='details');
  if(details) details.classList.toggle('active',view==='details');
  document.querySelectorAll('[data-container-view]').forEach(button=>button.classList.toggle('active',button.dataset.containerView===view));
}

function filterContainers(){
  const search=document.getElementById('container-search');
  if(!search) return;
  const term=search.value.trim().toLowerCase();
  document.querySelectorAll('.container-card').forEach(card=>card.classList.toggle('hidden',!card.dataset.search.includes(term)));
  document.querySelectorAll('.container-detail-row').forEach(row=>{
    const hidden=!row.dataset.search.includes(term);
    row.classList.toggle('hidden',hidden);
    const progress=row.nextElementSibling;
    if(progress?.classList.contains('detail-progress-row')) progress.classList.toggle('hidden',hidden || !progress.dataset.active);
  });
}

function ensureProgress(container){
  if(container.classList.contains('container-card')){
    let box=container.querySelector('.backup-progress');
    if(!box){
      box=document.createElement('div');box.className='backup-progress';
      box.innerHTML=`<div class="progress-head"><strong>${t('backup_running')}</strong><span class="progress-percent">0%</span></div><div class="progress-track"><div class="progress-bar"></div></div><div class="progress-message">${t('preparing_backup')}</div><details class="progress-log"><summary>Live log</summary><div class="progress-log-lines"></div></details>`;
      container.querySelector('.card-actions').prepend(box);
    }
    return box;
  }
  const row=container.closest('.container-detail-row');
  const progressRow=row?.nextElementSibling;
  if(!progressRow) return null;
  progressRow.dataset.active='true';progressRow.classList.remove('hidden');
  let box=progressRow.querySelector('.backup-progress');
  if(!box){box=document.createElement('div');box.className='backup-progress';box.innerHTML=`<div class="progress-head"><strong>${t('backup_running')}</strong><span class="progress-percent">0%</span></div><div class="progress-track"><div class="progress-bar"></div></div><div class="progress-message">${t('preparing_backup')}</div><details class="progress-log"><summary>Live log</summary><div class="progress-log-lines"></div></details>`;progressRow.querySelector('td').appendChild(box)}
  return box;
}

function renderJob(container,button,job){
  const box=ensureProgress(container);if(!box)return;
  const progress=Number(job.progress||0);box.classList.add('active');
  box.querySelector('.progress-percent').textContent=`${progress}%`;box.querySelector('.progress-bar').style.width=`${progress}%`;box.querySelector('.progress-message').textContent=job.message||t('backup_running_dots');
  box.querySelector('.progress-log-lines').innerHTML=(job.log||[]).map(line=>`<div><time>${line.time}</time><span>${escapeHtml(line.message)}</span></div>`).join('');
  if(job.status==='success'){box.classList.add('success');button.disabled=false;button.textContent=t('back_up_now')}
  else if(job.status==='error'){box.classList.add('error');button.disabled=false;button.textContent=t('try_again')}
}

async function pollJob(jobId,container,button){
  try{
    const response=await fetch(`/api/jobs/${jobId}`,{headers:{Accept:'application/json'}});const job=await response.json();
    if(!response.ok)throw new Error(job.detail||job.error||t('job_status_failed'));
    renderJob(container,button,job);
    if(job.status==='success'){showToast(`${job.container_name}: ${t('backup_completed')}`,'success');setTimeout(()=>location.reload(),1500);return}
    if(job.status==='error'){showToast(`${job.container_name}: ${job.error||job.message}`,'error');return}
    setTimeout(()=>pollJob(jobId,container,button),1000);
  }catch(error){button.disabled=false;button.textContent=t('try_again');showToast(error.message,'error')}
}

function bindBackupForms(scope=document){
  scope.querySelectorAll('.backup-form:not([data-bound])').forEach(form=>{
    form.dataset.bound='true';
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      const container=form.closest('.container-card')||form.closest('.container-detail-row');
      const button=form.querySelector('button[type="submit"]');
      if(button.disabled)return;
      button.disabled=true;button.innerHTML=`<span class="spinner"></span> ${t('backup_starting')}`;
      const box=ensureProgress(container);box.className='backup-progress active';box.querySelector('.progress-percent').textContent='0%';box.querySelector('.progress-bar').style.width='0%';box.querySelector('.progress-message').textContent=t('sending_request');
      showToast(t('backup_started'),'info');
      const containerId=form.action.split('/').filter(Boolean).pop();
      try{
        const response=await fetch(`/api/backup/${containerId}`,{method:'POST',body:new FormData(form),headers:{Accept:'application/json'}});const job=await response.json();
        if(!response.ok)throw new Error(job.error||job.detail||t('backup_start_failed'));
        renderJob(container,button,job);pollJob(job.id,container,button);
      }catch(error){button.disabled=false;button.textContent=t('try_again');box.classList.add('error');box.querySelector('.progress-message').textContent=error.message;showToast(error.message,'error')}
    });
  });
}

document.addEventListener('DOMContentLoaded',()=>{
  markTranslatable();injectContainerViewStyles();ensureContainerViewToggle();rebuildContainerDetails();
  const language=document.getElementById('language-select');
  if(language){language.value=currentLanguage;language.addEventListener('change',()=>applyLanguage(language.value))}
  applyLanguage(currentLanguage);

  const tabs=document.querySelectorAll('.nav-item');const panels=document.querySelectorAll('.tab-panel');
  function openTab(name){tabs.forEach(button=>button.classList.toggle('active',button.dataset.tab===name));panels.forEach(panel=>panel.classList.toggle('active',panel.id===`tab-${name}`));localStorage.setItem('contbak-tab',name)}
  tabs.forEach(button=>button.addEventListener('click',()=>openTab(button.dataset.tab)));
  document.querySelectorAll('[data-open-tab]').forEach(button=>button.addEventListener('click',()=>openTab(button.dataset.openTab)));
  const savedTab=localStorage.getItem('contbak-tab');if(savedTab&&document.getElementById(`tab-${savedTab}`))openTab(savedTab);

  const search=document.getElementById('container-search');if(search)search.addEventListener('input',filterContainers);
  setContainerView(localStorage.getItem('contbak-container-view')||'cards');
  bindBackupForms();

  const selectAll=document.getElementById('select-all-backups');if(selectAll)selectAll.addEventListener('change',()=>document.querySelectorAll('.backup-select').forEach(item=>item.checked=selectAll.checked));
  const exportForm=document.getElementById('export-form');if(exportForm)exportForm.addEventListener('submit',event=>{if(!document.querySelector('.backup-select:checked')){event.preventDefault();showToast(t('select_backup'),'error')}});
  const importForm=document.getElementById('import-form');if(importForm)importForm.addEventListener('submit',async event=>{event.preventDefault();const button=importForm.querySelector('button');const status=document.getElementById('import-status');button.disabled=true;button.innerHTML=`<span class="spinner"></span>${t('import_running')}`;status.textContent=t('upload_verifying');try{const response=await fetch(importForm.action,{method:'POST',body:new FormData(importForm)});const data=await response.json();if(!response.ok)throw new Error(data.error||t('import_failed'));status.textContent=`Import completed: ${data.results.length} backup(s) processed.`;showToast(t('import_success'),'success');setTimeout(()=>location.reload(),900)}catch(error){status.textContent=error.message;showToast(error.message,'error')}finally{button.disabled=false;button.textContent=t('upload_import')}});
});
