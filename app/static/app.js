(() => {
  const tabs = document.querySelectorAll('.nav-item');
  const panels = document.querySelectorAll('.tab-panel');

  function openTab(name) {
    tabs.forEach(btn => btn.classList.toggle('active', btn.dataset.tab === name));
    panels.forEach(panel => panel.classList.toggle('active', panel.id === `tab-${name}`));
    localStorage.setItem('dockback-tab', name);
  }

  tabs.forEach(btn => btn.addEventListener('click', () => openTab(btn.dataset.tab)));
  document.querySelectorAll('[data-open-tab]').forEach(btn => btn.addEventListener('click', () => openTab(btn.dataset.openTab)));

  const savedTab = localStorage.getItem('dockback-tab');
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
})();
