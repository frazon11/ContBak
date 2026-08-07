(() => {
  const lang = () => localStorage.getItem('contbak-language') || 'en';
  const tx = (en, de) => lang() === 'de' ? de : en;

  function toast(message, type='info') {
    if (typeof showToast === 'function') showToast(message, type);
  }

  function status(message, type='info') {
    const box=document.getElementById('import-status');
    if(!box)return;
    box.textContent=message;box.style.whiteSpace='pre-wrap';box.style.fontWeight='700';
    box.style.color=type==='error'?'#fca5a5':type==='success'?'#86efac':'#93c5fd';
  }

  function ensureStyles(){
    if(document.getElementById('restore-recreate-style'))return;
    const s=document.createElement('style');s.id='restore-recreate-style';s.textContent=`
      .restore-modal-backdrop{position:fixed;inset:0;background:rgba(2,6,23,.76);z-index:2000;display:grid;place-items:center;padding:20px}
      .restore-modal{width:min(720px,100%);max-height:90vh;overflow:auto;background:var(--surface);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:20px}
      .restore-modal h3{margin:0 0 6px}.restore-modal p{color:var(--muted);font-size:13px}.restore-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin:18px 0}.restore-grid label{display:grid;gap:6px;color:var(--muted);font-size:12px}.restore-grid input,.restore-grid select{padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--surface-2);color:var(--text)}
      .restore-summary{padding:12px;border:1px solid var(--line);border-radius:9px;background:var(--surface-2);font-size:12px}.restore-summary strong{display:block;margin-bottom:5px}.restore-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:18px}.restore-warning{color:#fcd34d!important}.restore-config-only{margin-top:10px;padding:10px;border:1px solid #854d0e;border-radius:8px;background:rgba(133,77,14,.16);color:#fde68a!important}
      @media(max-width:650px){.restore-grid{grid-template-columns:1fr}}
    `;document.head.appendChild(s);
  }

  async function getInfo(path){
    const r=await fetch(`/api/restore-info?path=${encodeURIComponent(path)}`,{headers:{Accept:'application/json'},cache:'no-store'});
    const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||`HTTP ${r.status}`);return d;
  }

  function choose(info){
    return new Promise(resolve=>{
      ensureStyles();
      const bg=document.createElement('div');bg.className='restore-modal-backdrop';
      const containers=(info.containers||[]).map(c=>`<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)} — ${escapeHtml(c.image)} (${escapeHtml(c.status)})</option>`).join('');
      const restorable=Number.isFinite(info.restorable_count)?info.restorable_count:(info.mounts||[]).filter(m=>m.archive).length;
      const skipped=Number.isFinite(info.skipped_count)?info.skipped_count:(info.mounts||[]).filter(m=>!m.archive).length;
      const configOnly=info.config_only===true || restorable===0;
      const configNotice=configOnly?`<p class="restore-config-only">${tx('This backup contains no persistent mount archives. The container configuration can still be recreated, but no volume or bind-mount data will be restored.','Dieses Backup enthält keine persistenten Mount-Archive. Die Container-Konfiguration kann trotzdem neu erstellt werden, aber Volume- oder Bind-Mount-Daten werden nicht restauriert.')}</p>`:'';
      bg.innerHTML=`<div class="restore-modal" role="dialog" aria-modal="true">
        <h3>${tx('Restore container backup','Container-Backup wiederherstellen')}</h3>
        <p>${tx('Choose whether to restore into an existing container or recreate the original container from its saved Docker configuration.','Wähle, ob in einen vorhandenen Container restauriert oder der ursprüngliche Container aus der gespeicherten Docker-Konfiguration neu erstellt werden soll.')}</p>
        <div class="restore-summary"><strong>${escapeHtml(info.original_name||'—')}</strong>${tx('Image','Image')}: ${escapeHtml(info.image||'—')}<br>${tx('Restorable mounts','Wiederherstellbare Mounts')}: ${restorable}<br>${tx('Skipped/non-data mounts','Übersprungene/Nicht-Daten-Mounts')}: ${skipped}</div>
        ${configNotice}
        <div class="restore-grid">
          <label>${tx('Restore mode','Restore-Modus')}<select id="rr-mode"><option value="auto">${tx('Automatic: use existing or recreate if missing','Automatisch: vorhanden nutzen oder fehlenden neu erstellen')}</option><option value="existing">${tx('Restore data to existing container','Daten in vorhandenen Container restaurieren')}</option><option value="recreate">${tx('Recreate container from backup','Container aus Backup neu erstellen')}</option></select></label>
          <label>${tx('Target container','Zielcontainer')}<select id="rr-existing"><option value="">${tx('Original name / automatic','Originalname / automatisch')}</option>${containers}</select></label>
          <label>${tx('Container name for recreation','Containername bei Neuerstellung')}<input id="rr-name" value="${escapeHtml(info.original_name||'')}"></label>
          <label>${tx('Name conflict','Namenskonflikt')}<select id="rr-conflict"><option value="abort">${tx('Abort','Abbrechen')}</option><option value="replace">${tx('Replace existing container','Vorhandenen Container ersetzen')}</option><option value="rename">${tx('Create under a new name','Unter neuem Namen erstellen')}</option></select></label>
        </div>
        <p class="restore-warning">${tx('Warning: Replace removes the existing container before recreation. Persistent data is only replaced after preflight succeeds.','Warnung: Ersetzen entfernt den vorhandenen Container vor der Neuerstellung. Persistente Daten werden erst nach erfolgreicher Vorprüfung ersetzt.')}</p>
        <div class="restore-actions"><button class="btn btn-secondary" id="rr-cancel">${tx('Cancel','Abbrechen')}</button><button class="btn btn-danger" id="rr-start">${configOnly?tx('Recreate configuration','Konfiguration wiederherstellen'):tx('Start restore','Restore starten')}</button></div>
      </div>`;
      document.body.appendChild(bg);
      const mode=bg.querySelector('#rr-mode'),existing=bg.querySelector('#rr-existing'),name=bg.querySelector('#rr-name');
      function sync(){existing.disabled=mode.value==='recreate';name.disabled=mode.value==='existing';}
      mode.addEventListener('change',sync);sync();
      bg.querySelector('#rr-cancel').onclick=()=>{bg.remove();resolve(null)};
      bg.addEventListener('click',e=>{if(e.target===bg){bg.remove();resolve(null)}});
      bg.querySelector('#rr-start').onclick=()=>{
        const selected={mode:mode.value,target_name:mode.value==='existing'?(existing.value||info.original_name):(name.value.trim()||info.original_name),conflict:bg.querySelector('#rr-conflict').value};
        bg.remove();resolve(selected);
      };
    });
  }

  async function refresh(){
    const r=await fetch('/',{headers:{Accept:'text/html'},cache:'no-store'});if(!r.ok)return;
    const doc=new DOMParser().parseFromString(await r.text(),'text/html');
    const old=document.querySelector('#tab-backups .table-card'),fresh=doc.querySelector('#tab-backups .table-card');
    if(old&&fresh)old.replaceWith(fresh);
  }

  document.addEventListener('submit',async e=>{
    const form=e.target.closest?.('form[action="/restore"]');if(!form)return;
    e.preventDefault();e.stopImmediatePropagation();
    const path=form.querySelector('input[name="path"]')?.value;if(!path)return;
    const button=form.querySelector('button[type="submit"]');const original=button?.textContent||'Restore';
    try{
      const info=await getInfo(path);const options=await choose(info);if(!options)return;
      if(button){button.disabled=true;button.innerHTML=`<span class="spinner"></span>${tx('Restoring…','Wiederherstellung …')}`}
      status(tx('Restore started. Follow progress in Logs or docker logs ContBak.','Restore gestartet. Fortschritt unter Logs oder mit docker logs ContBak verfolgen.'),'info');
      const data=new FormData();data.set('path',path);data.set('mode',options.mode);data.set('target_name',options.target_name);data.set('conflict',options.conflict);
      const r=await fetch('/restore',{method:'POST',body:data,headers:{Accept:'application/json'}});const result=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(result.error||result.detail||`HTTP ${r.status}`);
      const message=result.message||tx('Restore completed successfully.','Wiederherstellung erfolgreich abgeschlossen.');status(message,'success');toast(message,'success');await refresh();
    }catch(err){const message=tx('Restore failed: ','Wiederherstellung fehlgeschlagen: ')+err.message;status(message,'error');toast(message,'error')}
    finally{if(button){button.disabled=false;button.textContent=original}}
  },true);

  function escapeHtml(value){const d=document.createElement('div');d.textContent=String(value??'');return d.innerHTML}
})();
