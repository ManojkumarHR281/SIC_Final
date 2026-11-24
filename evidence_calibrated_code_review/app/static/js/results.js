document.addEventListener('DOMContentLoaded', () => {
  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const search = qs('#findingSearch');
  const severity = qs('#severityFilter');
  const confidence = qs('#confidenceFilter');
  const category = qs('#categoryFilter');
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

  const filter = () => {
    const query = search?.value.toLowerCase() || '';
    let visible = 0;
    qsa('.finding-card').forEach(card => {
      const show = (!severity?.value || card.dataset.severity === severity.value)
        && (!confidence?.value || card.dataset.confidence === confidence.value)
        && (!category?.value || card.dataset.category === category.value)
        && (!query || (card.dataset.search || '').includes(query));
      card.hidden = !show;
      if (show) visible++;
    });
    const empty = qs('#noMatches');
    if (empty) empty.hidden = visible > 0;
    const counter = qs('#visibleCount');
    if (counter) counter.textContent = visible;
  };

  [search, severity, confidence, category].forEach(input => {
    input?.addEventListener('input', () => { qsa('#quickFilters button').forEach(node => node.classList.remove('active')); filter(); });
    input?.addEventListener('change', () => { qsa('#quickFilters button').forEach(node => node.classList.remove('active')); filter(); });
  });

  qsa('[data-quick-severity]').forEach(button => button.addEventListener('click', () => {
    if (severity) severity.value = button.dataset.quickSeverity;
    if (confidence) confidence.value = '';
    qsa('#quickFilters button').forEach(node => node.classList.toggle('active', node === button));
    filter();
  }));
  qsa('[data-quick-confidence]').forEach(button => button.addEventListener('click', () => {
    if (confidence) confidence.value = button.dataset.quickConfidence;
    if (severity) severity.value = '';
    qsa('#quickFilters button').forEach(node => node.classList.toggle('active', node === button));
    filter();
  }));
  qs('[data-quick-clear]')?.addEventListener('click', () => {
    [search, severity, confidence, category].forEach(input => { if (input) input.value = ''; });
    qsa('#quickFilters button').forEach(node => node.classList.toggle('active', node.dataset.quickClear !== undefined));
    filter();
  });

  qsa('.finding-head').forEach(head => head.addEventListener('click', () => head.closest('.finding-card')?.classList.toggle('open')));
  qs('#expandAll')?.addEventListener('click', () => qsa('.finding-card:not([hidden])').forEach(card => card.classList.add('open')));
  qs('#collapseAll')?.addEventListener('click', () => qsa('.finding-card').forEach(card => card.classList.remove('open')));
  qsa('[data-open-first]').forEach(button => button.addEventListener('click', () => button.closest('.finding-card')?.classList.add('open')));

  const ring = qs('#qualityRing');
  const ringValue = qs('#qualityValue');
  if (ring) {
    const target = Number(ring.dataset.value || 0);
    const start = performance.now();
    const tick = time => {
      const progress = Math.min(1, (time - start) / 900);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(target * eased);
      ring.style.setProperty('--value', current);
      if (ringValue) ringValue.textContent = current;
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  setTimeout(() => qsa('.severity-bar i').forEach(bar => bar.style.width = `${bar.dataset.width || 0}%`), 80);

  qsa('[data-ai-action]').forEach(button => button.addEventListener('click', async () => {
    const card = button.closest('.finding-card');
    openModal('AI explanation', '<p><span class="spinner"></span> Preparing explanation…</p>');
    try {
      const response = await fetch('/api/ai/explain', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: button.dataset.aiAction,
          code: card?.dataset.code || '',
          finding: {
            title: card?.dataset.title, description: card?.dataset.description,
            severity: card?.dataset.severity, recommendation: card?.dataset.recommendation
          }
        })
      });
      const result = await response.json();
      const body = qs('#appModalBody');
      if (body) body.innerHTML = result.ok ? `<p>${escapeHtml(result.text || result.message || '').replace(/\n/g, '<br>')}</p>` : `<div class="warning-box">${escapeHtml(result.error || result.reason || 'The AI endpoint is unavailable.')}</div>`;
    } catch (error) {
      const body = qs('#appModalBody');
      if (body) body.innerHTML = '<div class="warning-box">The AI endpoint is unavailable.</div>';
    }
  }));

  qsa('[data-fix]').forEach(button => button.addEventListener('click', () => {
    const card = button.closest('.finding-card');
    const code = card?.dataset.fix || '';
    const before = card?.dataset.snippet || '';
    openModal('Suggested fix', `
      <p>${escapeHtml(card?.dataset.recommendation || '')}</p>
      <div class="diff-grid">
        <div><div class="diff-label">Current</div><pre class="code-snippet diff-before">${escapeHtml(before)}</pre></div>
        <div><div class="diff-label">Suggested</div><pre class="code-snippet diff-after">${escapeHtml(code)}</pre></div>
      </div>
      <div class="mt-3 d-flex gap-2 flex-wrap">
        <button class="btn btn-light" id="copyFix"><i class="bi bi-clipboard me-2"></i>Copy fix</button>
        <button class="btn btn-outline-light" id="copyRecommendation"><i class="bi bi-clipboard me-2"></i>Copy recommendation</button>
      </div>`);
    qs('#copyFix')?.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(code); toast('Fix copied.'); }
      catch (error) { toast('Clipboard unavailable.', 'error'); }
    });
    qs('#copyRecommendation')?.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(card?.dataset.recommendation || ''); toast('Recommendation copied.'); }
      catch (error) { toast('Clipboard unavailable.', 'error'); }
    });
  }));

  filter();
});
