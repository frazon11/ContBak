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
        <div class="progress-head"><strong>Backup läuft</strong><span class="progress-percent">0%</span></div>
        <div class="progress-track"><div class="progress-bar"></div></div>
        <div class="progress-message">Backup wird vorbereitet …</div>
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
    box.querySelector('.progress-message').textContent = job.message || 'Backup läuft …';
    const lines = box.querySelector('.progress-log-lines');
    lines.innerHTML = (job.log || []).map(line => `<div><time>${line.time}</time><span>${escapeHtml(line.message)}</span></div>`).join('');

    if (job.status === 'success') {
      box.classList.add('success');
      button.disabled = false;
      button.innerHTML = 'Jetzt sichern';
    } else if (job.status === 'error') {
      box.classList.add('error');
      button.disabled = false;
      button.innerHTML = 'Erneut versuchen';
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
      if (!response.ok) throw new Error(job.detail || job.error || 'Jobstatus konnte nicht gelesen werden.');
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
      button.textContent = 'Erneut versuchen';
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
      button.innerHTML = '<span class="spinner"></span> Backup startet …';
      const box = ensureProgress(card);
      box.className = 'backup-progress active';
      box.querySelector('.progress-percent').textContent = '0%';
      box.querySelector('.progress-bar').style.width = '0%';
      box.querySelector('.progress-message').textContent = 'Anfrage wird gesendet …';
      toast('Backup wurde gestartet.', 'info');

      const containerId = form.action.split('/').filter(Boolean).pop();
      try {
        const response = await fetch(`/api/backup/${containerId}`, {
          method: 'POST',
          body: new FormData(form),
          headers: {'Accept': 'application/json'}
        });
        const job = await response.json();
        if (!response.ok) throw new Error(job.error || job.detail || 'Backup konnte nicht gestartet werden.');
        renderJob(card, button, job);
        pollJob(job.id, card, button);
      } catch (error) {
        button.disabled = false;
        button.textContent = 'Erneut versuchen';
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
if(exportForm)exportForm.addEventListener('submit',e=>{if(!document.querySelector('.backup-select:checked')){e.preventDefault();showToast('Bitte mindestens ein Backup auswählen.','error')}});
const importForm=document.getElementById('import-form');
if(importForm)importForm.addEventListener('submit',async e=>{e.preventDefault();const btn=importForm.querySelector('button');const status=document.getElementById('import-status');btn.disabled=true;btn.innerHTML='<span class="spinner"></span>Import läuft …';status.textContent='Datei wird hochgeladen und geprüft …';try{const r=await fetch(importForm.action,{method:'POST',body:new FormData(importForm)});const data=await r.json();if(!r.ok)throw new Error(data.error||'Import fehlgeschlagen');status.textContent=`Import abgeschlossen: ${data.results.length} Backup(s) verarbeitet.`;showToast('Backup erfolgreich importiert.','success');setTimeout(()=>location.reload(),900)}catch(err){status.textContent=err.message;showToast(err.message,'error')}finally{btn.disabled=false;btn.textContent='Upload & Import'}});
