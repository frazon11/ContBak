const I18N = {
  en: {
    backup_running:'Backup running', preparing_backup:'Preparing backup…', backup_running_dots:'Backup running…', back_up_now:'Back up now', try_again:'Try again', job_status_failed:'Could not read job status.', backup_completed:'Backup completed.', backup_starting:'Starting backup…', sending_request:'Sending request…', backup_started:'Backup started.', backup_start_failed:'Could not start backup.', select_backup:'Please select at least one backup.', import_running:'Importing…', upload_verifying:'Uploading and verifying file…', import_failed:'Import failed', import_success:'Backup imported successfully.', upload_import:'Upload & import'
  },
  de: {
    backup_running:'Backup läuft', preparing_backup:'Backup wird vorbereitet …', backup_running_dots:'Backup läuft …', back_up_now:'Jetzt sichern', try_again:'Erneut versuchen', job_status_failed:'Jobstatus konnte nicht gelesen werden.', backup_completed:'Backup abgeschlossen.', backup_starting:'Backup startet …', sending_request:'Anfrage wird gesendet …', backup_started:'Backup wurde gestartet.', backup_start_failed:'Backup konnte nicht gestartet werden.', select_backup:'Bitte mindestens ein Backup auswählen.', import_running:'Import läuft …', upload_verifying:'Datei wird hochgeladen und geprüft …', import_failed:'Import fehlgeschlagen', import_success:'Backup erfolgreich importiert.', upload_import:'Upload & Import'
  }
};
let currentLanguage = localStorage.getItem('contbak-language') || 'en';
function t(key){ return (I18N[currentLanguage] && I18N[currentLanguage][key]) || I18N.en[key] || key; }
const STATIC_DE = {
  'Dashboard':'Übersicht','Schedules':'Zeitpläne','Logs':'Protokoll','Docker connection active':'Docker-Verbindung aktiv','Docker Backup':'Docker-Sicherung','Back up all':'Alle sichern','Container status':'Containerstatus','Current Docker environment status':'Aktueller Zustand der Docker-Umgebung','Show all':'Alle anzeigen','Latest backups':'Letzte Sicherungen','Most recent backup sets':'Neueste Backup-Sätze','Back up individual services and manage schedules':'Einzelne Dienste sichern und Zeitpläne verwalten','Show mounts':'Mounts anzeigen','Stop container':'Container stoppen','Back up now':'Jetzt sichern','Save schedule':'Zeitplan speichern','Restore, download, export and import':'Wiederherstellen, herunterladen, exportieren und importieren','Import backup':'Backup importieren','Rename duplicate':'Duplikat umbenennen','Skip duplicate':'Duplikat überspringen','Replace duplicate':'Duplikat ersetzen','Upload & import':'Upload & Import','Export selected':'Ausgewählte exportieren','Date/time':'Zeitpunkt','Size':'Größe','Path':'Pfad','Action':'Aktion','Automatic daily backups':'Automatische tägliche Sicherungen','Execution':'Ausführung','Delete':'Löschen','Results of recent backup and restore operations':'Ergebnisse der letzten Backup- und Restore-Vorgänge','Message':'Meldung','Search containers…':'Container suchen …','Language':'Sprache'
};
function applyLanguage(lang){
  currentLanguage=lang; localStorage.setItem('contbak-language',lang); document.documentElement.lang=lang;
  document.querySelectorAll('[data-en-text]').forEach(el=>{el.textContent=lang==='de'?(STATIC_DE[el.dataset.enText]||el.dataset.enText):el.dataset.enText});
  document.querySelectorAll('option[data-en-text]').forEach(el=>{el.textContent=lang==='de'?(STATIC_DE[el.dataset.enText]||el.dataset.enText):el.dataset.enText});
  const search=document.getElementById('container-search'); if(search) search.placeholder=lang==='de'?'Container suchen …':'Search containers…';
}
function markTranslatable(){
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(n=>{const v=n.nodeValue.trim(); if(v && STATIC_DE[v]){const span=document.createElement('span');span.dataset.enText=v;span.textContent=v;n.parentNode.replaceChild(span,n);}});
}
document.addEventListener('DOMContentLoaded',()=>{markTranslatable();const sel=document.getElementById('language-select');if(sel){sel.value=currentLanguage;sel.addEventListener('change',()=>applyLanguage(sel.value));}applyLanguage(currentLanguage);});
(() => {
  const tabs = document.querySelectorAll('.nav-item');
  const panels = document.querySelectorAll('.tab-panel');

  function openTab(name) {
    tabs.forEach(btn => btn.classList.toggle('active', btn.dataset.tab === name));
    panels.forEach(panel => panel.classList.toggle('active', panel.id === `tab-${name}`));
    localStorage.setItem('contbak-tab', name);
  }

  tabs.forEach(btn => btn.addEventListener('click', () => openTab(btn.dataset.tab)));
  document.querySelectorAll('[data-open-tab]').forEach(btn => btn.addEventListener('click', () => openTab(btn.dataset.openTab)));

  const savedTab = localStorage.getItem('contbak-tab');
  if (savedTab && document.getElementById(`tab-${savedTab}`)) openTab(savedTab);

  const search = document.getElementById('container-search');
  if (search) {
    search.addEventListener('input', () => {
      const term = search.value.trim().toLowerCase();
      document.querySelectorAll('.container-card').forEach(card => {
        card.classList.toggle('hidden', !card.dataset.search.includes(term));
      });
    });
  }

  function toast(message, type = 'info') {
    let host = document.querySelector('.toast-host');
    if (!host) {
      host = document.createElement('div');
      host.className = 'toast-host';
      document.body.appendChild(host);
    }
    const item = document.createElement('div');
    item.className = `toast toast-${type}`;
    item.textContent = message;
    host.appendChild(item);
    requestAnimationFrame(() => item.classList.add('show'));
    setTimeout(() => {
      item.classList.remove('show');
      setTimeout(() => item.remove(), 250);
    }, 5000);
  }

  function ensureProgress(card) {
    let box = card.querySelector('.backup-progress');
    if (!box) {
      box = document.createElement('div');
      box.className = 'backup-progress';
      box.innerHTML = `
        <div class="progress-head"><strong>${t('backup_running')}</strong><span class="progress-percent">0%</span></div>
        <div class="progress-track"><div class="progress-bar"></div></div>
        <div class="progress-message">${t('preparing_backup')}</div>
        <details class="progress-log"><summary>Live-Protokoll</summary><div class="progress-log-lines"></div></details>`;
      card.querySelector('.card-actions').prepend(box);
    }
    return box;
  }

  function renderJob(card, button, job) {
    const box = ensureProgress(card);
    const progress = Number(job.progress || 0);
    box.classList.add('active');
    box.querySelector('.progress-percent').textContent = `${progress}%`;
    box.querySelector('.progress-bar').style.width = `${progress}%`;
    box.querySelector('.progress-message').textContent = job.message || t('backup_running_dots');
    const lines = box.querySelector('.progress-log-lines');
    lines.innerHTML = (job.log || []).map(line => `<div><time>${line.time}</time><span>${escapeHtml(line.message)}</span></div>`).join('');

    if (job.status === 'success') {
      box.classList.add('success');
      button.disabled = false;
      button.innerHTML = t('back_up_now');
    } else if (job.status === 'error') {
      box.classList.add('error');
      button.disabled = false;
      button.innerHTML = t('try_again');
    }
  }

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = String(value ?? '');
    return div.innerHTML;
  }

  async function pollJob(jobId, card, button) {
    try {
      const response = await fetch(`/api/jobs/${jobId}`, {headers: {'Accept': 'application/json'}});
      const job = await response.json();
      if (!response.ok) throw new Error(job.detail || job.error || t('job_status_failed'));
      renderJob(card, button, job);
      if (job.status === 'success') {
        toast(`${job.container_name}: Backup abgeschlossen.`, 'success');
        setTimeout(() => window.location.reload(), 1500);
        return;
      }
      if (job.status === 'error') {
        toast(`${job.container_name}: ${job.error || job.message}`, 'error');
        return;
      }
      setTimeout(() => pollJob(jobId, card, button), 1000);
    } catch (error) {
      button.disabled = false;
      button.textContent = t('try_again');
      toast(error.message, 'error');
    }
  }

  document.querySelectorAll('.backup-form').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const card = form.closest('.container-card');
      const button = form.querySelector('button[type="submit"]');
      if (button.disabled) return;
      button.disabled = true;
      button.innerHTML = `<span class="spinner"></span> ${t('backup_starting')}`;
      const box = ensureProgress(card);
      box.className = 'backup-progress active';
      box.querySelector('.progress-percent').textContent = '0%';
      box.querySelector('.progress-bar').style.width = '0%';
      box.querySelector('.progress-message').textContent = t('sending_request');
      toast(t('backup_started'), 'info');

      const containerId = form.action.split('/').filter(Boolean).pop();
      try {
        const response = await fetch(`/api/backup/${containerId}`, {
          method: 'POST',
          body: new FormData(form),
          headers: {'Accept': 'application/json'}
        });
        const job = await response.json();
        if (!response.ok) throw new Error(job.error || job.detail || t('backup_start_failed'));
        renderJob(card, button, job);
        pollJob(job.id, card, button);
      } catch (error) {
        button.disabled = false;
        button.textContent = t('try_again');
        box.classList.add('error');
        box.querySelector('.progress-message').textContent = error.message;
        toast(error.message, 'error');
      }
    });
  });
})();

const selectAllBackups=document.getElementById('select-all-backups');
if(selectAllBackups)selectAllBackups.addEventListener('change',()=>document.querySelectorAll('.backup-select').forEach(x=>x.checked=selectAllBackups.checked));
const exportForm=document.getElementById('export-form');
if(exportForm)exportForm.addEventListener('submit',e=>{if(!document.querySelector('.backup-select:checked')){e.preventDefault();showToast(t('select_backup'),'error')}});
const importForm=document.getElementById('import-form');
if(importForm)importForm.addEventListener('submit',async e=>{e.preventDefault();const btn=importForm.querySelector('button');const status=document.getElementById('import-status');btn.disabled=true;btn.innerHTML=`<span class="spinner"></span>${t('import_running')}`;status.textContent=t('upload_verifying');try{const r=await fetch(importForm.action,{method:'POST',body:new FormData(importForm)});const data=await r.json();if(!r.ok)throw new Error(data.error||t('import_failed'));status.textContent=`Import abgeschlossen: ${data.results.length} Backup(s) verarbeitet.`;showToast(t('import_success'),'success');setTimeout(()=>location.reload(),900)}catch(err){status.textContent=err.message;showToast(err.message,'error')}finally{btn.disabled=false;btn.textContent=t('upload_import')}});
