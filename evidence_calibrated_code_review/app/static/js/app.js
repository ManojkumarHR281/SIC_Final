const qs = (selector, root = document) => root.querySelector(selector);
const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function toast(message, type = 'success') {
  const stack = qs('#toastStack');
  if (!stack) return;
  const node = document.createElement('div');
  node.className = `toast ${type}`;
  node.innerHTML = `<i class="bi bi-${type === 'error' ? 'exclamation-octagon' : 'check-circle'} me-2"></i>${message}`;
  stack.appendChild(node);
  setTimeout(() => node.remove(), 3500);
}

function openModal(title, html) {
  const modal = qs('#appModal');
  if (!modal) return;
  qs('#appModalTitle').textContent = title;
  qs('#appModalBody').innerHTML = html;
  modal.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  const modal = qs('#appModal');
  if (modal) modal.hidden = true;
  const palette = qs('#commandPalette');
  if (palette) palette.hidden = true;
  document.body.style.overflow = '';
}

function effectiveTheme() {
  const saved = localStorage.getItem('ecr-theme') || 'dark';
  return saved === 'system'
    ? (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
    : saved;
}

function applyTheme(choice, persist = true) {
  if (persist) localStorage.setItem('ecr-theme', choice);
  document.documentElement.dataset.theme = effectiveTheme();
  const button = qs('#themeButton i');
  if (button) button.className = effectiveTheme() === 'light' ? 'bi bi-sun' : 'bi bi-moon-stars';
  qsa('[data-theme-choice]').forEach(item => item.classList.toggle('active', item.dataset.themeChoice === choice));
}

let reviewCache = null;
async function loadReviews() {
  if (reviewCache) return reviewCache;
  const response = await fetch('/api/reviews');
  reviewCache = response.ok ? await response.json() : [];
  return reviewCache;
}

document.addEventListener('DOMContentLoaded', () => {
  applyTheme(localStorage.getItem('ecr-theme') || 'dark', false);

  const sidebar = qs('#sidebar');
  const toggle = qs('#menuToggle');
  const backdrop = qs('#sidebarBackdrop');
  const collapse = qs('#sidebarCollapse');
  toggle?.addEventListener('click', () => sidebar?.classList.toggle('open'));
  backdrop?.addEventListener('click', () => sidebar?.classList.remove('open'));
  collapse?.addEventListener('click', () => {
    sidebar?.classList.toggle('collapsed');
    localStorage.setItem('ecr-sidebar', sidebar?.classList.contains('collapsed') ? 'collapsed' : 'expanded');
  });
  if (localStorage.getItem('ecr-sidebar') === 'collapsed') sidebar?.classList.add('collapsed');

  qsa('[data-dismiss-alert]').forEach(button => button.addEventListener('click', () => button.closest('.app-alert')?.remove()));
  qsa('[data-close-modal]').forEach(button => button.addEventListener('click', closeModal));
  qs('#appModal')?.addEventListener('click', event => { if (event.target.id === 'appModal') closeModal(); });

  const popovers = [['#themeButton', '#themeMenu'], ['#notificationButton', '#notificationMenu'], ['#userButton', '#userMenu']];
  popovers.forEach(([buttonSelector, menuSelector]) => {
    qs(buttonSelector)?.addEventListener('click', event => {
      event.stopPropagation();
      const menu = qs(menuSelector);
      const wasHidden = menu.hidden;
      popovers.forEach(([, other]) => { const node = qs(other); if (node) node.hidden = true; });
      menu.hidden = !wasHidden;
    });
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.popover')) popovers.forEach(([, selector]) => { const node = qs(selector); if (node) node.hidden = true; });
  });
  qsa('[data-theme-choice]').forEach(item => item.addEventListener('click', () => {
    applyTheme(item.dataset.themeChoice);
    toast(`Theme set to ${item.dataset.themeChoice}.`);
  }));

  const search = qs('#globalSearch');
  const searchResults = qs('#searchResults');
  let searchIndex = 0;
  let searchItems = [];

  const renderSearch = async () => {
    const term = search.value.trim().toLowerCase();
    if (!term) { searchResults.hidden = true; return; }
    const reviews = await loadReviews();
    const groups = [
      { title: 'Reviews', items: reviews.filter(r => (r.title || '').toLowerCase().includes(term)).slice(0, 5).map(r => ({ label: r.title, meta: `#${r.id}`, href: `/reviews/${r.id}`, icon: 'bi-file-earmark-text' })) },
      { title: 'Files', items: reviews.flatMap(r => (r.file_names || []).filter(name => name.toLowerCase().includes(term)).map(name => ({ label: name, meta: r.title, href: `/reviews/${r.id}`, icon: 'bi-file-code' }))).slice(0, 5) },
      { title: 'Findings', items: reviews.flatMap(r => (r.findings || []).filter(f => (f.title || '').toLowerCase().includes(term)).slice(0, 4).map(f => ({ label: f.title, meta: `${f.severity} · ${f.rule_id || ''}`, href: `/reviews/${r.id}`, icon: 'bi-bug' }))).slice(0, 6) },
      { title: 'Reports', items: reviews.filter(r => (r.title || '').toLowerCase().includes(term)).slice(0, 3).map(r => ({ label: `${r.title} report`, meta: 'PDF / JSON / CSV', href: `/reports`, icon: 'bi-file-earmark-bar-graph' })) },
    ].filter(group => group.items.length);
    searchItems = groups.flatMap(group => group.items);
    searchIndex = 0;
    searchResults.innerHTML = groups.map(group => `
      <div class="search-group"><div class="search-group-title">${group.title}</div>
      ${group.items.map(item => `<div class="search-group-item" data-href="${item.href}"><i class="bi ${item.icon}"></i><span>${item.label}</span><small>${item.meta}</small></div>`).join('')}
      </div>`).join('') || '<div class="popover-item"><div><strong>No results</strong><small>Try a review title, file name or finding.</small></div></div>';
    searchResults.hidden = false;
    highlightSearch();
  };

  const highlightSearch = () => qsa('.search-group-item', searchResults).forEach((node, index) => node.classList.toggle('selected', index === searchIndex));
  let searchTimer;
  search?.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(renderSearch, 140); });
  search?.addEventListener('keydown', event => {
    if (!searchItems.length) return;
    if (event.key === 'ArrowDown') { event.preventDefault(); searchIndex = (searchIndex + 1) % searchItems.length; highlightSearch(); }
    if (event.key === 'ArrowUp') { event.preventDefault(); searchIndex = (searchIndex - 1 + searchItems.length) % searchItems.length; highlightSearch(); }
    if (event.key === 'Enter') { event.preventDefault(); window.location.href = searchItems[searchIndex].href; }
    if (event.key === 'Escape') { searchResults.hidden = true; search.blur(); }
  });
  searchResults?.addEventListener('click', event => {
    const item = event.target.closest('[data-href]');
    if (item) window.location.href = item.dataset.href;
  });
  document.addEventListener('click', event => { if (!event.target.closest('.global-search-wrap')) searchResults.hidden = true; });

  const palette = qs('#commandPalette');
  const commandInput = qs('#commandInput');
  const commandList = qs('#commandList');
  let commandItems = [];
  let commandIndex = 0;

  const renderCommands = async () => {
    const term = (commandInput.value || '').trim().toLowerCase();
    const reviews = await loadReviews();
    const commands = [
      { label: 'Dashboard', hint: 'Page', icon: 'bi-grid-1x2', href: '/' },
      { label: 'New Review', hint: 'Page', icon: 'bi-plus-square', href: '/review/new' },
      { label: 'Review History', hint: 'Page', icon: 'bi-clock-history', href: '/history' },
      { label: 'Security Analysis', hint: 'Page', icon: 'bi-shield-lock', href: '/security' },
      { label: 'Code Quality', hint: 'Page', icon: 'bi-stars', href: '/quality' },
      { label: 'Analytics', hint: 'Page', icon: 'bi-activity', href: '/analytics' },
      { label: 'Reports', hint: 'Page', icon: 'bi-file-earmark-bar-graph', href: '/reports' },
      { label: 'Settings', hint: 'Page', icon: 'bi-sliders2', href: '/settings' },
      { label: 'Help and Documentation', hint: 'Page', icon: 'bi-question-circle', href: '/help' },
      { label: 'Start new review', hint: 'Action', icon: 'bi-lightning', href: '/review/new' },
      { label: 'Upload source file', hint: 'Action', icon: 'bi-upload', href: '/review/new', action: 'upload' },
      { label: 'Change theme', hint: 'Action', icon: 'bi-circle-half', action: 'theme' },
      ...reviews.slice(0, 8).map(r => ({ label: r.title, hint: `Review #${r.id}`, icon: 'bi-file-earmark-text', href: `/reviews/${r.id}` })),
    ].filter(item => item.label.toLowerCase().includes(term));
    commandItems = commands;
    commandIndex = 0;
    commandList.innerHTML = commands.map((item, index) => `<div class="command-item ${index === 0 ? 'selected' : ''}" data-index="${index}"><i class="bi ${item.icon}"></i><span>${item.label}</span><small>${item.hint}</small></div>`).join('') || '<div class="popover-item"><div><strong>No commands found</strong></div></div>';
  };

  const runCommand = async item => {
    if (!item) return;
    if (item.action === 'theme') {
      closeModal();
      qs('#themeMenu').hidden = false;
      return;
    }
    if (item.action === 'upload') {
      window.location.href = '/review/new?upload=1';
      return;
    }
    window.location.href = item.href;
  };

  const openPalette = async () => {
    palette.hidden = false;
    commandInput.value = '';
    document.body.style.overflow = 'hidden';
    await renderCommands();
    commandInput.focus();
  };
  qs('#commandButton')?.addEventListener('click', openPalette);
  commandInput?.addEventListener('input', renderCommands);
  commandInput?.addEventListener('keydown', event => {
    if (!commandItems.length) return;
    if (event.key === 'ArrowDown') { event.preventDefault(); commandIndex = (commandIndex + 1) % commandItems.length; qsa('.command-item').forEach((n, i) => n.classList.toggle('selected', i === commandIndex)); }
    if (event.key === 'ArrowUp') { event.preventDefault(); commandIndex = (commandIndex - 1 + commandItems.length) % commandItems.length; qsa('.command-item').forEach((n, i) => n.classList.toggle('selected', i === commandIndex)); }
    if (event.key === 'Enter') { event.preventDefault(); runCommand(commandItems[commandIndex]); }
  });
  commandList?.addEventListener('click', event => {
    const node = event.target.closest('[data-index]');
    if (node) runCommand(commandItems[Number(node.dataset.index)]);
  });
  palette?.addEventListener('click', event => { if (event.target.id === 'commandPalette') closeModal(); });

  qsa('form[data-confirm]').forEach(form => form.addEventListener('submit', event => { if (!window.confirm(form.dataset.confirm)) event.preventDefault(); }));
  qsa('[data-auto-submit]').forEach(control => control.addEventListener('change', () => {
    control.form?.querySelector('[data-loading]')?.classList.add('loading');
    control.form?.submit();
  }));
  qsa('form').forEach(form => form.addEventListener('submit', event => {
    const button = event.submitter || qs('[type="submit"]', form);
    if (!button || button.disabled) return;
    button.dataset.originalHtml = button.innerHTML;
    button.innerHTML = '<span class="spinner me-2"></span>Working…';
    button.disabled = true;
  }));
  window.matchMedia('(prefers-color-scheme: light)').addEventListener?.('change', () => {
    if ((localStorage.getItem('ecr-theme') || 'dark') === 'system') applyTheme('system', false);
  });
  qsa('[data-copy]').forEach(button => button.addEventListener('click', async () => {
    const target = qs(button.dataset.copy);
    if (!target) return;
    try { await navigator.clipboard.writeText(target.value ?? target.textContent ?? ''); toast('Copied to clipboard.'); }
    catch (error) { toast('Clipboard unavailable in this browser.', 'error'); }
  }));

  document.addEventListener('keydown', event => {
    const modifier = event.ctrlKey || event.metaKey;
    if (modifier && event.key.toLowerCase() === 'k') { event.preventDefault(); openPalette(); }
    if (modifier && event.key.toLowerCase() === 'j') { event.preventDefault(); search?.focus(); search?.select(); }
    if (modifier && event.key.toLowerCase() === 'b') { event.preventDefault(); toggleSidebar(); }
    if (event.key === 'Escape') { closeModal(); searchResults.hidden = true; }
  });

  function toggleSidebar() { sidebar?.classList.toggle('open'); }

  if (window.Chart) {
    Chart.defaults.color = '#94A3B8';
    Chart.defaults.borderColor = 'rgba(148,163,184,.12)';
    Chart.defaults.font.family = 'DM Sans, sans-serif';
  }
});
