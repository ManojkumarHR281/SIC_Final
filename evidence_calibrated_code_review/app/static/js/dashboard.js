document.addEventListener('DOMContentLoaded', () => {
  const palette = {
    Critical: '#F43F5E', High: '#FB7185', Medium: '#F59E0B', Low: '#10B981', Informational: '#22D3EE',
    HIGH: '#10B981', MEDIUM: '#F59E0B', LOW: '#F43F5E',
    Security: '#8B5CF6', Bug: '#F43F5E', Syntax: '#F59E0B', Performance: '#22D3EE', Quality: '#6366F1'
  };
  const parse = el => { try { return JSON.parse(el.dataset.values || el.dataset.timeline || '{}'); } catch (error) { return {}; } };
  const colorsFor = keys => keys.map(key => palette[key] || '#8B5CF6');

  const now = new Date();
  const hour = now.getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const heading = document.querySelector('#welcomeHeading');
  if (heading) heading.textContent = `${greeting} — here's your review intelligence`;
  const dateNode = document.querySelector('#todayDate');
  if (dateNode) dateNode.textContent = now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

  document.querySelectorAll('[data-count]').forEach(node => {
    const target = Number(node.dataset.count || 0);
    const duration = 750;
    const start = performance.now();
    const tick = time => {
      const progress = Math.min(1, (time - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      node.textContent = Math.round(target * eased);
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  const timelineData = parse(document.querySelector('[data-timeline]') || { dataset: { timeline: '[]' } });
  const sparkValue = kind => Array.isArray(timelineData) ? timelineData.map(row => row[kind] || 0) : [];
  document.querySelectorAll('[data-spark]').forEach(svg => {
    const values = sparkValue(svg.dataset.spark === 'reviews' ? 'reviews' : svg.dataset.spark === 'findings' ? 'findings' : 'quality');
    if (!values.length) return;
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const points = values.map((value, index) => {
      const x = values.length === 1 ? 0 : index / (values.length - 1) * 100;
      const y = 26 - ((value - min) / (max - min || 1)) * 22;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    svg.innerHTML = `<polyline points="${points}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" opacity=".65"/>`;
  });

  const bar = selector => {
    const canvas = document.querySelector(selector);
    if (!canvas || !window.Chart) return;
    const values = parse(canvas), keys = Object.keys(values);
    if (!keys.length) return;
    new Chart(canvas, { type: 'bar', data: { labels: keys, datasets: [{ data: Object.values(values), backgroundColor: colorsFor(keys), borderRadius: 6, maxBarThickness: 44 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: 'rgba(148,163,184,.12)' } } } } });
  };
  const doughnut = selector => {
    const canvas = document.querySelector(selector);
    if (!canvas || !window.Chart) return;
    const values = parse(canvas), keys = Object.keys(values);
    if (!keys.length || !Object.values(values).some(Boolean)) return;
    new Chart(canvas, { type: 'doughnut', data: { labels: keys, datasets: [{ data: Object.values(values), backgroundColor: colorsFor(keys), borderWidth: 0, hoverOffset: 6 }] }, options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 7, padding: 14 } } } } });
  };
  const line = (selector, key, color) => {
    const canvas = document.querySelector(selector);
    if (!canvas || !window.Chart) return;
    const rows = parse(canvas);
    if (!Array.isArray(rows) || !rows.length) return;
    new Chart(canvas, { type: 'line', data: { labels: rows.map(row => row.date), datasets: [{ label: key, data: rows.map(row => row[key]), borderColor: color, backgroundColor: `${color}22`, fill: true, tension: .35, pointRadius: 3, pointBackgroundColor: color }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: 'rgba(148,163,184,.12)' } } } } });
  };

  bar('#severityChart'); bar('#securityGroupsChart');
  doughnut('#confidenceChart'); doughnut('#categoriesChart');
  line('#timelineChart', 'reviews', '#8B5CF6');
  line('#findingsTimelineChart', 'findings', '#F43F5E');
  line('#qualityTrendChart', 'quality', '#10B981');

  const historySearch = document.querySelector('#historySearch');
  historySearch?.addEventListener('input', () => {
    const value = historySearch.value.toLowerCase();
    document.querySelectorAll('#historyTable tbody tr').forEach(row => row.hidden = !row.dataset.search.includes(value));
  });
});
