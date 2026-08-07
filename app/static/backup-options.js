(() => {
  const lang=()=>localStorage.getItem('contbak-language')||'en';
  const tx=(en,de)=>lang()==='de'?de:en;
  let dialogOpen=false;

  function ensureStyles(){
    if(document.getElementById('backup-options-style'))return;
    const s=document.createElement('style');s.id='backup-options-style';s.textContent=`
      .backup-options-backdrop{position:fixed;inset:0;background:rgba(2,6,23,.76);z-index:2100;display:grid;place-items:center;padding:20px}
      .backup-options-modal{width:min(760px,100%);max-height:90vh;overflow:auto;background:var(--surface);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:20px}
      .backup-options-modal h3{margin:0 0 5px}.backup-options-modal>p{margin:0;color:var(--muted);font-size:13px}.bo-section{margin-top:17px;border:1px solid var(--line);border-radius:10px;overflow:hidden}.bo-section-head{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;background:var(--surface-2);font-size:12px;font-weight:800}.bo-row{display:grid;grid-template-columns:minmax(230px,1fr) 120px minmax(180px,1fr);gap:10px;align-items:center;padding:10px 12px;border-top:1px solid var(--line);font-size:12px}.bo-row:first-of-type{border-top:0}.bo-choice{display:flex;align-items:center;gap:9px;min-width:0}.bo-choice span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bo-muted{color:var(--muted)}.bo-skipped{opacity:.62}.bo-note{padding:9px 12px;color:var(--muted);font-size:11px;border-top:1px solid var(--line)}.bo-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:18px}.bo-switch{display:flex;align-items:center;gap:8px;margin-top:15px;font-size:12px}.bo-config{display:flex;align-items:flex-start;gap:9px;padding:12px;border:1px solid var(--line);border-radius:10px;margin-top:17px}.bo-config strong{display:block;margin-bottom:3px}.bo-config small{color:var(--muted)}
      @media(max-width:680px){.bo-row{grid-template-columns:1fr}.bo-row>div:nth-child(2){padding-left:27px}.bo-row>div:nth-child(3){padding-left:27px}}
    `;document.head.appendChild(s);
  }

  async function backupInfo(containerId){
    const r=await fetch(`/api/backup-info/${encodeURIComponent(containerId)}`,{headers:{Accept:'application/json'},cache:'no-store'});
    const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||`HTTP ${r.status}`);return d;
  }

  function choose(info,initialStop){
    return new Promise(resolve=>{
      ensureStyles();dialogOpen=true;
      const bg=document.createElement('div');bg.className='backup-options-backdrop';
      const eligible=(info.mounts||[]).filter(m=>m.eligible);
      const skipped=(info.mounts||[]).filter(m=>!m.eligible);
      const rows=eligible.map((m,i)=>`<div class="bo-row"><label class="bo-choice"><input type="checkbox" class="bo-mount" value="${escapeHtml(m.destination||'')}" checked><span title="${escapeHtml(m.destination||'')}">${escapeHtml(m.destination||'—')}</span></label><div class="bo-muted">${escapeHtml(m.type||'mount')}</div><div class="bo-muted" title="${escapeHtml(m.source||'')}">${escapeHtml(m.source||'')}</div></div>`).join('');
      const skippedRows=skipped.map(m=>`<div class="bo-row bo-skipped"><label class="bo-choice"><input type="checkbox" disabled><span title="${escapeHtml(m.destination||'')}">${escapeHtml(m.destination||'—')}</span></label><div class="bo-muted">${escapeHtml(m.type||'mount')}</div><div class="bo-muted">${escapeHtml(m.skip_reason||tx('Not eligible for backup','Nicht sicherbar'))}</div></div>`).join('');
      bg.innerHTML=`<div class="backup-options-modal" role="dialog" aria-modal="true">
        <h3>${tx('Backup options','Backup-Optionen')}: ${escapeHtml(info.name||'')}</h3>
        <p>${escapeHtml(info.image||'')}</p>
        <label class="bo-config"><input type="checkbox" id="bo-config" checked><span><strong>${tx('Container configuration','Container-Konfiguration')}</strong><small>${tx('Image, environment, ports, labels, networks, restart policy, command and other Docker settings.','Image, Umgebungsvariablen, Ports, Labels, Netzwerke, Restart-Policy, Command und weitere Docker-Einstellungen.')}</small></span></label>
        <div class="bo-section"><div class="bo-section-head"><span>${tx('Persistent mounts','Persistente Mounts')} (${eligible.length})</span><label class="bo-choice"><input type="checkbox" id="bo-all" checked><span>${tx('Select all','Alle auswählen')}</span></label></div>${rows||`<div class="bo-note">${tx('No restorable persistent mounts detected.','Keine wiederherstellbaren persistenten Mounts erkannt.')}</div>`}</div>
        ${skipped.length?`<div class="bo-section"><div class="bo-section-head"><span>${tx('Automatically skipped','Automatisch übersprungen')} (${skipped.length})</span></div>${skippedRows}</div>`:''}
        <label class="bo-switch"><input type="checkbox" id="bo-stop" ${initialStop?'checked':''}><span>${tx('Stop container during backup for filesystem consistency','Container während des Backups für Dateisystem-Konsistenz stoppen')}</span></label>
        <div class="bo-actions"><button type="button" class="btn btn-secondary" id="bo-cancel">${tx('Cancel','Abbrechen')}</button><button type="button" class="btn btn-primary" id="bo-start">${tx('Start backup','Backup starten')}</button></div>
      </div>`;
      document.body.appendChild(bg);
      const all=bg.querySelector('#bo-all');const mounts=[...bg.querySelectorAll('.bo-mount')];
      const syncAll=()=>{all.checked=mounts.length>0&&mounts.every(c=>c.checked);all.indeterminate=mounts.some(c=>c.checked)&&!mounts.every(c=>c.checked)};
      all.addEventListener('change',()=>{mounts.forEach(c=>c.checked=all.checked);syncAll()});mounts.forEach(c=>c.addEventListener('change',syncAll));syncAll();
      const close=value=>{dialogOpen=false;bg.remove();resolve(value)};
      bg.querySelector('#bo-cancel').onclick=()=>close(null);bg.addEventListener('click',e=>{if(e.target===bg)close(null)});
      bg.querySelector('#bo-start').onclick=()=>close({includeConfig:bg.querySelector('#bo-config').checked,selectedMounts:mounts.filter(c=>c.checked).map(c=>c.value),stop:bg.querySelector('#bo-stop').checked});
    });
  }

  async function startBackup(form){
    const containerId=form.action.split('/').filter(Boolean).pop();if(!containerId)return;
    const container=form.closest('.container-card')||form.closest('.container-detail-row');const button=form.querySelector('button[type="submit"]');
    const originalStop=form.querySelector('input[name="stop"]')?.checked??false;
    const info=await backupInfo(containerId);const opts=await choose(info,originalStop||info.stop_default===true);if(!opts)return;
    if(button){button.disabled=true;button.innerHTML=`<span class="spinner"></span> ${typeof t==='function'?t('backup_starting'):tx('Starting backup…','Backup startet …')}`}
    if(typeof ensureProgress==='function'){const box=ensureProgress(container);if(box){box.className='backup-progress active';const msg=box.querySelector('.progress-message');if(msg)msg.textContent=tx('Sending backup selection…','Backup-Auswahl wird gesendet …')}}
    const data=new FormData();if(opts.stop)data.set('stop','on');if(opts.includeConfig)data.set('include_config','on');else data.set('include_config','off');data.set('mounts_json',JSON.stringify(opts.selectedMounts));
    const r=await fetch(`/api/backup/${encodeURIComponent(containerId)}`,{method:'POST',body:data,headers:{Accept:'application/json'}});const job=await r.json().catch(()=>({}));
    if(!r.ok)throw new Error(job.error||job.detail||`HTTP ${r.status}`);
    if(typeof showToast==='function')showToast(`${info.name}: ${tx('Backup started.','Backup gestartet.')}`,'info');
    if(typeof pollJob==='function')pollJob(job.id,container,button);
  }

  document.addEventListener('submit',async e=>{
    const form=e.target.closest?.('.backup-form');if(!form||dialogOpen)return;
    e.preventDefault();e.stopImmediatePropagation();
    try{await startBackup(form)}catch(err){const button=form.querySelector('button[type="submit"]');if(button){button.disabled=false;button.textContent=typeof t==='function'?t('try_again'):tx('Try again','Erneut versuchen')}if(typeof showToast==='function')showToast(err.message,'error')}
  },true);

  function escapeHtml(value){const d=document.createElement('div');d.textContent=String(value??'');return d.innerHTML}
})();
