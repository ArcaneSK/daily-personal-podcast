// Static-site episode browser: search + pagination, all client-side.
// No build step, no framework — works via file:// double-click.

(function () {
  const PAGE_SIZE = 10;

  const list = document.getElementById('episode-list');
  const searchInput = document.getElementById('search');
  const resultsCount = document.getElementById('results-count');
  const pagination = document.getElementById('pagination');
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');
  const pageIndicator = document.getElementById('page-indicator');
  const epCount = document.getElementById('episode-count');

  if (!list) return;

  // Snapshot every episode's searchable text once at load time.
  const items = Array.from(list.querySelectorAll('li.episode')).map((el) => ({
    el,
    date: el.dataset.date || '',
    title: el.dataset.title || '',
    text: el.textContent.toLowerCase(),
  }));

  if (epCount) epCount.textContent = `${items.length} episode${items.length === 1 ? '' : 's'}`;

  let filtered = items.slice();
  let page = 0;

  function readState() {
    const h = location.hash.replace(/^#/, '');
    const params = new URLSearchParams(h);
    const q = params.get('q') || '';
    const p = parseInt(params.get('page') || '0', 10) || 0;
    return { q, p };
  }

  function writeState(q, p) {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (p > 0) params.set('page', String(p));
    const newHash = params.toString();
    const target = newHash ? `#${newHash}` : '#';
    if (location.hash !== target) {
      history.replaceState(null, '', target);
    }
  }

  function applyFilter(query) {
    const q = query.trim().toLowerCase();
    if (!q) {
      filtered = items.slice();
    } else {
      filtered = items.filter((it) => it.text.includes(q));
    }
    page = 0;
    render();
  }

  function render() {
    // Hide everything, then show only the current page slice.
    items.forEach((it) => { it.el.hidden = true; });

    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (page >= totalPages) page = totalPages - 1;
    if (page < 0) page = 0;
    const start = page * PAGE_SIZE;
    const end = Math.min(start + PAGE_SIZE, total);

    for (let i = start; i < end; i++) {
      filtered[i].el.hidden = false;
    }

    if (resultsCount) {
      if (searchInput.value.trim()) {
        resultsCount.textContent = `${total} match${total === 1 ? '' : 'es'}`;
      } else {
        resultsCount.textContent = '';
      }
    }

    if (totalPages > 1) {
      pagination.hidden = false;
      pageIndicator.textContent = `Page ${page + 1} of ${totalPages}`;
      prevBtn.disabled = page === 0;
      nextBtn.disabled = page >= totalPages - 1;
    } else {
      pagination.hidden = true;
    }

    writeState(searchInput.value.trim(), page);
  }

  // Wiring
  searchInput.addEventListener('input', (e) => applyFilter(e.target.value));
  prevBtn.addEventListener('click', () => { page--; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); });
  nextBtn.addEventListener('click', () => { page++; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); });

  // Restore state from URL
  const { q, p } = readState();
  if (q) {
    searchInput.value = q;
    applyFilter(q);
  }
  if (p) {
    page = p;
  }
  render();

  // Keyboard: '/' focuses search, like a podcast app.
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });

  // Auto-collapse other accordions when one opens (one-at-a-time UX).
  list.addEventListener('toggle', (e) => {
    const opened = e.target;
    if (!(opened instanceof HTMLDetailsElement) || !opened.open) return;
    list.querySelectorAll('details[open]').forEach((d) => {
      if (d !== opened) d.open = false;
    });
  }, true);
})();
