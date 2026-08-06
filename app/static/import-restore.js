(() => {
  function text(en, de) {
    return (localStorage.getItem('contbak-language') || 'en') === 'de' ? de : en;
  }

  function setStatus(message, type = 'success') {
    const status = document.getElementById('import-status');
    if (!status) return;
    status.textContent = message;
    status.dataset.state = type;
    status.style.color = type === 'error' ? '#fca5a5' : type === 'info' ? '#93c5fd' : '#86efac';
    status.style.fontWeight = '700';
    status.style.whiteSpace = 'pre-wrap';
  }

  async function refreshBackupOverview() {
    const response = await fetch('/', {
      headers: { Accept: 'text/html' },
      cache: 'no-store'
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const html = await response.text();
    const parsed = new DOMParser().parseFromString(html, 'text/html');
    const currentTab = document.getElementById('tab-backups');
    const freshTab = parsed.getElementById('tab-backups');
    if (!currentTab || !freshTab) throw new Error('Backup overview not found.');

    const currentTable = currentTab.querySelector('.table-card');
    const freshTable = freshTab.querySelector('.table-card');
    if (!currentTable || !freshTable) throw new Error('Backup table not found.');
    currentTable.replaceWith(freshTable);

    const freshExportForm = freshTab.querySelector('#export-form');
    const currentExportForm = currentTab.querySelector('#export-form');
    if (freshExportForm && currentExportForm) currentExportForm.replaceWith(freshExportForm);

    const selectAll = document.getElementById('select-all-backups');
    if (selectAll) {
      selectAll.addEventListener('change', () => {
        document.querySelectorAll('.backup-select').forEach(item => {
          item.checked = selectAll.checked;
        });
      });
    }
    bindRestoreForms();
  }

  function bindImportForm() {
    const form = document.getElementById('import-form');
    if (!form || form.dataset.feedbackBound === 'true') return;
    form.dataset.feedbackBound = 'true';

    form.addEventListener('submit', async event => {
      event.preventDefault();
      event.stopImmediatePropagation();

      const button = form.querySelector('button[type="submit"]');
      const originalLabel = button ? button.textContent : '';
      if (button) {
        button.disabled = true;
        button.innerHTML = `<span class="spinner"></span>${text('Importing…', 'Import läuft …')}`;
      }
      setStatus(text('Uploading and verifying backup…', 'Backup wird hochgeladen und geprüft …'), 'info');

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { Accept: 'application/json' }
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || data.detail || text('Import failed.', 'Import fehlgeschlagen.'));

        const count = Array.isArray(data.results) ? data.results.length : 0;
        const message = text(
          `Import completed successfully. ${count} backup(s) processed.`,
          `Import erfolgreich abgeschlossen. ${count} Backup(s) verarbeitet.`
        );
        setStatus(message, 'success');
        if (typeof showToast === 'function') showToast(message, 'success');
        form.reset();

        try {
          await refreshBackupOverview();
        } catch (_) {
          localStorage.setItem('contbak-backup-message', message);
          localStorage.setItem('contbak-tab', 'backups');
          location.reload();
        }
      } catch (error) {
        setStatus(error.message, 'error');
        if (typeof showToast === 'function') showToast(error.message, 'error');
      } finally {
        if (button) {
          button.disabled = false;
          button.textContent = originalLabel || text('Upload & import', 'Upload & Import');
        }
      }
    }, true);
  }

  function bindRestoreForms() {
    document.querySelectorAll('form[action="/restore"]:not([data-feedback-bound])').forEach(form => {
      form.dataset.feedbackBound = 'true';
      form.removeAttribute('onsubmit');

      form.addEventListener('submit', async event => {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!confirm(text(
          'Really overwrite the existing data for this container?',
          'Vorhandene Daten dieses Containers wirklich überschreiben?'
        ))) return;

        const button = form.querySelector('button[type="submit"]');
        const originalLabel = button ? button.textContent : '';
        if (button) {
          button.disabled = true;
          button.innerHTML = `<span class="spinner"></span>${text('Restoring…', 'Wiederherstellung …')}`;
        }
        setStatus(text('Restore is running. The container may be stopped temporarily…', 'Wiederherstellung läuft. Der Container kann kurzzeitig gestoppt werden …'), 'info');

        try {
          const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { Accept: 'application/json' }
          });
          const data = await response.json().catch(async () => ({ error: await response.text().catch(() => '') }));
          if (!response.ok) {
            const detail = data.error || data.detail || `${data.type || 'RestoreError'}: HTTP ${response.status}`;
            throw new Error(detail);
          }

          const message = data.message || text('Restore completed successfully.', 'Wiederherstellung erfolgreich abgeschlossen.');
          setStatus(message, 'success');
          if (typeof showToast === 'function') showToast(message, 'success');
          await refreshBackupOverview();
        } catch (error) {
          const message = text('Restore failed: ', 'Wiederherstellung fehlgeschlagen: ') + error.message;
          setStatus(message, 'error');
          if (typeof showToast === 'function') showToast(message, 'error');
        } finally {
          if (button) {
            button.disabled = false;
            button.textContent = originalLabel || text('Restore', 'Wiederherstellen');
          }
        }
      }, true);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    localStorage.setItem('contbak-tab', localStorage.getItem('contbak-tab') || 'dashboard');
    bindImportForm();
    bindRestoreForms();

    const savedMessage = localStorage.getItem('contbak-backup-message');
    if (savedMessage) {
      localStorage.removeItem('contbak-backup-message');
      setStatus(savedMessage, 'success');
      if (typeof showToast === 'function') showToast(savedMessage, 'success');
    }
  });
})();
