
(() => {
  const REPO = 'Frazon11/ContBak';
  const API = `https://api.github.com/repos/${REPO}/releases?per_page=20`;

  function versionParts(value) {
    return String(value || '').replace(/^v/i, '').split('.').map(part => Number.parseInt(part, 10) || 0);
  }

  function compareVersions(left, right) {
    const a = versionParts(left);
    const b = versionParts(right);
    for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
      const difference = (a[index] || 0) - (b[index] || 0);
      if (difference !== 0) return difference;
    }
    return 0;
  }

  function currentVersion() {
    const label = document.querySelector('.version-label')?.textContent || '';
    return (label.match(/\d+\.\d+\.\d+/) || ['0.0.0'])[0];
  }

  function injectStyles() {
    if (document.getElementById('contbak-release-styles')) return;
    const style = document.createElement('style');
    style.id = 'contbak-release-styles';
    style.textContent = `
      .update-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:18px}
      .update-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:18px;box-shadow:var(--shadow)}
      .update-card span,.update-card small{display:block;color:var(--muted)}
      .update-card strong{display:block;font-size:22px;margin:8px 0}
      .update-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px}
      .release-list{display:grid;gap:10px}
      .release-row{display:grid;grid-template-columns:130px minmax(0,1fr) auto;gap:16px;align-items:center;padding:14px 16px;border-bottom:1px solid var(--line)}
      .release-row:last-child{border-bottom:0}.release-row p{margin:4px 0 0;color:var(--muted);font-size:12px}
      .release-current{border-left:3px solid var(--primary)}.update-ok{color:#86efac}.update-available{color:#fcd34d}.update-error{color:#fca5a5}
      @media(max-width:760px){.update-summary{grid-template-columns:1fr}.release-row{grid-template-columns:1fr}.release-row .right{text-align:left}}
    `;
    document.head.appendChild(style);
  }

  function injectPanel() {
    const nav = document.querySelector('.nav');
    const main = document.querySelector('main');
    if (!nav || !main || document.getElementById('tab-updates')) return;

    const navButton = document.createElement('button');
    navButton.className = 'nav-item';
    navButton.dataset.tab = 'updates';
    navButton.textContent = currentLanguage === 'de' ? 'Versionen' : 'Updates';
    nav.appendChild(navButton);

    const panel = document.createElement('section');
    panel.className = 'tab-panel';
    panel.id = 'tab-updates';
    panel.innerHTML = `
      <div class="section-heading">
        <div>
          <h2>${currentLanguage === 'de' ? 'Versionen & Updates' : 'Versions & Updates'}</h2>
          <p>${currentLanguage === 'de' ? 'Installierte Version prüfen und GitHub Releases anzeigen' : 'Check the installed version and browse GitHub Releases'}</p>
        </div>
      </div>
      <div class="update-summary">
        <article class="update-card"><span>${currentLanguage === 'de' ? 'Installiert' : 'Installed'}</span><strong id="installed-version">v${currentVersion()}</strong><small>ContBak</small></article>
        <article class="update-card"><span>${currentLanguage === 'de' ? 'Neuester Release' : 'Latest release'}</span><strong id="latest-version">–</strong><small id="latest-date">${currentLanguage === 'de' ? 'Noch nicht geprüft' : 'Not checked yet'}</small></article>
        <article class="update-card"><span>Status</span><strong id="update-status">–</strong><small id="update-message">${currentLanguage === 'de' ? 'Update-Prüfung starten' : 'Run an update check'}</small></article>
      </div>
      <div class="update-actions">
        <button class="btn btn-primary" type="button" id="check-updates">${currentLanguage === 'de' ? 'Nach Updates suchen' : 'Check for updates'}</button>
        <a class="btn btn-secondary" href="https://github.com/${REPO}/releases" target="_blank" rel="noopener">GitHub Releases</a>
      </div>
      <div class="table-card"><div class="panel-header"><div><h2>${currentLanguage === 'de' ? 'Versionshistorie' : 'Version history'}</h2><p>${currentLanguage === 'de' ? 'Automatisch aus GitHub Releases geladen' : 'Loaded automatically from GitHub Releases'}</p></div></div><div class="release-list" id="release-list"><div class="empty-state">${currentLanguage === 'de' ? 'Noch keine Release-Daten geladen.' : 'No release data loaded yet.'}</div></div></div>`;
    main.appendChild(panel);

    navButton.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(button => button.classList.toggle('active', button === navButton));
      document.querySelectorAll('.tab-panel').forEach(item => item.classList.toggle('active', item === panel));
      localStorage.setItem('contbak-tab', 'updates');
      loadReleases();
    });
    panel.querySelector('#check-updates').addEventListener('click', loadReleases);

    if (localStorage.getItem('contbak-tab') === 'updates') navButton.click();
  }

  async function loadReleases() {
    const button = document.getElementById('check-updates');
    const status = document.getElementById('update-status');
    const message = document.getElementById('update-message');
    const list = document.getElementById('release-list');
    if (!button || !status || !message || !list) return;

    button.disabled = true;
    button.textContent = currentLanguage === 'de' ? 'Prüfe …' : 'Checking…';
    status.textContent = '…';
    message.textContent = currentLanguage === 'de' ? 'GitHub wird abgefragt.' : 'Contacting GitHub.';

    try {
      const response = await fetch(API, {headers: {Accept: 'application/vnd.github+json'}});
      if (!response.ok) throw new Error(`GitHub API: HTTP ${response.status}`);
      const releases = await response.json();
      if (!Array.isArray(releases) || releases.length === 0) {
        status.textContent = currentLanguage === 'de' ? 'Keine Releases' : 'No releases';
        status.className = 'update-error';
        message.textContent = currentLanguage === 'de' ? 'GitHub enthält noch keine veröffentlichten Releases.' : 'GitHub does not contain any published releases yet.';
        list.innerHTML = `<div class="empty-state">${message.textContent}</div>`;
        return;
      }

      const latest = releases[0];
      const installed = currentVersion();
      const latestVersion = String(latest.tag_name || '').replace(/^v/i, '');
      document.getElementById('latest-version').textContent = latest.tag_name;
      document.getElementById('latest-date').textContent = new Date(latest.published_at).toLocaleString();

      if (compareVersions(latestVersion, installed) > 0) {
        status.textContent = currentLanguage === 'de' ? 'Update verfügbar' : 'Update available';
        status.className = 'update-available';
        message.textContent = `${latest.tag_name} ${currentLanguage === 'de' ? 'ist verfügbar.' : 'is available.'}`;
      } else {
        status.textContent = currentLanguage === 'de' ? 'Aktuell' : 'Up to date';
        status.className = 'update-ok';
        message.textContent = currentLanguage === 'de' ? 'Die installierte Version ist aktuell.' : 'The installed version is current.';
      }

      list.innerHTML = releases.map(release => {
        const tag = escapeHtml(release.tag_name || release.name || 'Release');
        const title = escapeHtml(release.name || release.tag_name || 'Release');
        const date = new Date(release.published_at).toLocaleString();
        const current = compareVersions(String(release.tag_name).replace(/^v/i, ''), installed) === 0;
        return `<article class="release-row ${current ? 'release-current' : ''}"><div><strong>${tag}</strong><p>${escapeHtml(date)}</p></div><div><strong>${title}</strong><p>${current ? (currentLanguage === 'de' ? 'Installierte Version' : 'Installed version') : (release.prerelease ? 'Pre-release' : 'Stable release')}</p></div><div class="right"><a class="btn btn-secondary btn-small" href="${escapeHtml(release.html_url)}" target="_blank" rel="noopener">${currentLanguage === 'de' ? 'Öffnen' : 'Open'}</a></div></article>`;
      }).join('');
    } catch (error) {
      status.textContent = currentLanguage === 'de' ? 'Fehler' : 'Error';
      status.className = 'update-error';
      message.textContent = error.message;
      list.innerHTML = `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    } finally {
      button.disabled = false;
      button.textContent = currentLanguage === 'de' ? 'Nach Updates suchen' : 'Check for updates';
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    injectStyles();
    injectPanel();
  });
})();
