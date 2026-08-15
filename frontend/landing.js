document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('demoInput');
  const btn = document.getElementById('demoScanBtn');
  const result = document.getElementById('demoResult');
  const verdictEl = document.getElementById('demoVerdict');
  const scoreEl = document.getElementById('demoScore');
  const flagsEl = document.getElementById('demoFlags');

  document.querySelectorAll('[data-demo]').forEach(b => {
    b.addEventListener('click', () => { input.value = b.dataset.demo; scanDemo(); });
  });
  btn.addEventListener('click', scanDemo);

  async function scanDemo() {
    const content = input.value.trim();
    if (!content) { input.focus(); return; }
    btn.classList.add('is-loading'); btn.disabled = true;
    result.className = 'landing-demo__result';
    try {
      const res = await fetch('/api/scan/demo', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({content}) });
      const d = await res.json();
      if (!res.ok) { verdictEl.textContent = d.message || 'Could not scan.'; result.classList.add('is-visible'); return; }
      const labels = { safe:'Safe', suspicious:'Suspicious', scam:'Likely Scam' };
      verdictEl.textContent = labels[d.verdict] || d.verdict;
      scoreEl.textContent = `Risk score: ${d.score}/100`;
      flagsEl.textContent = d.explanation || (d.flags?.length ? 'Signals: ' + d.flags.join(', ') : 'No specific red flags detected.');
      result.className = 'landing-demo__result is-visible landing-demo__result--' + d.verdict;
      result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch(e) {
      verdictEl.textContent = 'Connection error. Please try again.';
      result.classList.add('is-visible');
    } finally {
      btn.classList.remove('is-loading'); btn.disabled = false;
    }
  }
});