document.addEventListener('DOMContentLoaded', () => {
  const scanForm=document.getElementById('scanForm'), scanInput=document.getElementById('scanInput'), scanBtn=document.getElementById('scanBtn'), clearBtn=document.getElementById('clearBtn'), charCount=document.getElementById('charCount'), scanError=document.getElementById('scanError');
  const screenshotDrop=document.getElementById('screenshotDrop'), screenshotFile=document.getElementById('screenshotFile');
  const verdictPanel=document.getElementById('verdictPanel'), verdictBadge=document.getElementById('verdictBadge'), riskLevelBadge=document.getElementById('riskLevelBadge'), verdictScore=document.getElementById('verdictScore'), verdictTime=document.getElementById('verdictTime'), flagList=document.getElementById('flagList'), verdictExp=document.getElementById('verdictExplanation'), highlightBox=document.getElementById('highlightBox');
  const scanAnotherBtn=document.getElementById('scanAnotherBtn'), copyResultBtn=document.getElementById('copyResultBtn');
  const historyList=document.getElementById('historyList'), historyEmpty=document.getElementById('historyEmpty'), upgradeNudge=document.getElementById('upgradeNudge');
  const topbarAvatar=document.getElementById('topbarAvatar'), topbarName=document.getElementById('topbarName'), typeHint=document.getElementById('typeHint'), scannerTitle=document.getElementById('scannerTitle'), scannerSub=document.getElementById('scannerSub');

  let csrfToken='', lastResult=null, activeType='message', lastScannedText='', selectedScreenshotFile=null;

  const TYPES = {
    message: { label:'Message', title:'Scan a message', sub:"Paste a WhatsApp, SMS, or any suspicious text below.", hint:'Paste a WhatsApp message, SMS, or any suspicious text below.', placeholder:'Paste the suspicious message here…', mode:'text', examples:[{label:'Lottery scam',text:'Congratulations! You have won $5,000,000! Click here to claim: http://bit.ly/claim-now. Act NOW!'},{label:'Safe message',text:'Hey, are we still on for lunch tomorrow at 1pm?'}]},
    website: { label:'Website', title:'Scan a website URL', sub:"Paste any link or website URL to check safety.", hint:'Paste the full URL including https://', placeholder:'Paste a URL, e.g. https://example.com', mode:'text', examples:[{label:'Phishing URL',text:'http://bit.ly/verify-your-bank-account-now'},{label:'Safe site',text:'https://www.google.com'}]},
    email: { label:'Email', title:'Scan an email', sub:"Paste the full email content.", hint:'Include subject line, sender, and full body for best results.', placeholder:'Paste the email content here…', mode:'text', examples:[{label:'Phishing email',text:'Subject: Urgent: Verify Account\nFrom: security@paypa1.com\n\nYour account has been limited. Click here to verify: http://bit.ly/verify'},{label:'Safe email',text:'Subject: Meeting reminder\nFrom: colleague@company.com\n\nJust a reminder about our 3pm meeting.'}]},
    phone: { label:'Phone', title:'Check a phone number', sub:"Enter any number to check for scam reports.", hint:'Include the country code, e.g. +234...', placeholder:'Enter a phone number…', mode:'text', examples:[{label:'Suspicious number',text:'+1 (800) 555-SCAM — called claiming I won a prize and needs a $500 processing fee.'}]},
    screenshot: { label:'Screenshot', title:'Scan a screenshot', sub:"Upload a screenshot or paste extracted text.", hint:'Upload a screenshot OR paste the text below.', placeholder:'Or paste the text from your screenshot…', mode:'screenshot', examples:[{label:'WhatsApp scam',text:'Screenshot text: "I am a widow with $4.5 million to transfer. Send bank details urgently."'}]},
  };

  async function init() {
    try { const r=await fetch('/api/csrf-token',{credentials:'same-origin'}); csrfToken=(await r.json()).csrf_token||''; if(window.VeridictAd) window.VeridictAd.init(csrfToken); } catch(e){}
    try { const r=await fetch('/api/me',{credentials:'same-origin'}); if(r.status===401){window.location.href='/login';return;} const me=await r.json(); topbarAvatar.textContent=(me.full_name||me.username||'V').charAt(0).toUpperCase(); topbarName.textContent=me.full_name||me.username; } catch(e){}
    const params=new URLSearchParams(window.location.search); const urlType=params.get('type');
    setActiveType(urlType && TYPES[urlType] ? urlType : 'message');
    await Promise.all([loadStats(), loadHistory()]);
  }

  function setActiveType(type) {
    activeType=type; const cfg=TYPES[type];
    document.querySelectorAll('.sc-type-btn').forEach(b => b.classList.toggle('is-active', b.dataset.type===type));
    scannerTitle.textContent=cfg.title; scannerSub.textContent=cfg.sub; typeHint.textContent=cfg.hint; scanInput.placeholder=cfg.placeholder;
    screenshotDrop.hidden = cfg.mode!=='screenshot';
    const ex=document.getElementById('quickExamples'); ex.innerHTML='';
    cfg.examples.forEach(e => { const b=document.createElement('button'); b.type='button'; b.className='sc-ex-btn'; b.textContent=e.label; b.addEventListener('click',()=>{scanInput.value=e.text;scanInput.dispatchEvent(new Event('input'));}); ex.appendChild(b); });
    verdictPanel.classList.remove('is-visible'); clearError(); selectedScreenshotFile=null;
    const url=new URL(window.location.href); url.searchParams.set('type',type); window.history.replaceState({},'',url.toString());
  }
  document.querySelectorAll('.sc-type-btn').forEach(b => b.addEventListener('click', () => setActiveType(b.dataset.type)));

  scanInput.addEventListener('input', () => { const l=scanInput.value.length; charCount.textContent=`${l} / 5000`; if(scanError.classList.contains('is-visible'))clearError(); });
  clearBtn.addEventListener('click', () => { scanInput.value=''; charCount.textContent='0 / 5000'; verdictPanel.classList.remove('is-visible'); clearError(); selectedScreenshotFile=null; if(activeType==='screenshot') scanInput.placeholder=TYPES.screenshot.placeholder; scanInput.focus(); });

  if (screenshotDrop && screenshotFile) {
    screenshotDrop.addEventListener('dragover', e => { e.preventDefault(); screenshotDrop.classList.add('is-drag'); });
    screenshotDrop.addEventListener('dragleave', () => screenshotDrop.classList.remove('is-drag'));
    screenshotDrop.addEventListener('drop', e => { e.preventDefault(); screenshotDrop.classList.remove('is-drag'); if(e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });
    screenshotFile.addEventListener('change', () => { if(screenshotFile.files[0]) handleFile(screenshotFile.files[0]); });
  }
  function handleFile(file) {
    if (file.size > 5*1024*1024) { showError('File too large — max 5MB.'); return; }
    const okTypes = ['image/png','image/jpeg','image/jpg','image/webp'];
    if (!okTypes.includes(file.type)) { showError('Unsupported image type — use PNG, JPG, or WEBP.'); return; }
    selectedScreenshotFile = file;
    clearError();
    scanInput.value = '';
    scanInput.placeholder = `Selected: ${file.name} — click "Scan" to read and check it, or paste text instead.`;
    charCount.textContent = '0 / 5000';
  }

  function showError(msg) { scanError.textContent=msg; scanError.classList.add('is-visible'); }
  function clearError() { scanError.textContent=''; scanError.classList.remove('is-visible'); }
  function setLoading(v) { scanBtn.classList.toggle('is-loading',v); scanBtn.disabled=v; }

  scanForm.addEventListener('submit', async e => {
    e.preventDefault(); clearError();

    // Screenshot mode with a real file selected: upload it for OCR instead
    // of scanning whatever text happens to be in the textarea.
    if (activeType === 'screenshot' && selectedScreenshotFile) {
      setLoading(true); verdictPanel.classList.remove('is-visible');
      try {
        const fd = new FormData();
        fd.append('file', selectedScreenshotFile);
        const res = await fetch('/api/scan/screenshot', { method:'POST', credentials:'same-origin', headers:{'X-CSRFToken':csrfToken}, body: fd });
        const data = await res.json();
        if (!res.ok) {
          if (data.upgrade_required && window.VeridictAd) { window.VeridictAd.show(reward => { loadStats(); showError('You earned '+reward.bonus_granted+' bonus scans! Try again.'); }); }
          else { showError(data.message || 'Could not read that image.'); }
          return;
        }
        lastScannedText = data.extracted_text || '';
        lastResult = data; displayVerdict(data, true); await Promise.all([loadStats(), loadHistory()]);
        selectedScreenshotFile = null;
      } catch { showError('Connection error. Please try again.'); }
      finally { setLoading(false); }
      return;
    }

    const content=scanInput.value.trim();
    if (!content) { showError('Paste something to scan first, or upload a screenshot.'); scanInput.focus(); return; }
    setLoading(true); verdictPanel.classList.remove('is-visible');
    lastScannedText = content;
    try {
      const res=await fetch('/api/scan',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({content,type:activeType})});
      const data=await res.json();
      if (!res.ok) {
        if (data.upgrade_required && window.VeridictAd) { window.VeridictAd.show(reward => { loadStats(); showError('You earned '+reward.bonus_granted+' bonus scans! Try again.'); }); }
        else { upgradeNudge.classList.add('is-visible'); showError(data.message||'Could not run that scan.'); }
        return;
      }
      lastResult=data; displayVerdict(data,true); await Promise.all([loadStats(), loadHistory()]);
    } catch { showError('Connection error. Please try again.'); }
    finally { setLoading(false); }
  });

  function renderDeepAnalysis(findings) {
    let box = document.getElementById('deepAnalysisBox');
    if (box) box.remove();
    if (!findings || !findings.length) return;

    box = document.createElement('div');
    box.id = 'deepAnalysisBox';
    box.style.cssText = 'padding:14px 22px;border-top:1px solid var(--v-border);background:rgba(201,147,46,.05)';
    const label = document.createElement('div');
    label.style.cssText = 'font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--v-purple-lt);margin-bottom:10px;display:flex;align-items:center;gap:6px';
    label.innerHTML = '<span style="padding:1px 7px;border-radius:999px;background:var(--v-grad);color:#fff;font-size:.6rem">PRO</span> Priority Detection — deeper analysis';
    box.appendChild(label);

    findings.forEach(f => {
      const row = document.createElement('div');
      row.style.cssText = 'font-size:.82rem;color:var(--v-muted);padding-left:20px;position:relative;margin-bottom:8px;line-height:1.5';
      row.innerHTML = `<span style="position:absolute;left:0">•</span>${esc(f.note)}`;
      box.appendChild(row);
    });

    verdictPanel.appendChild(box);
  }

  function renderTypeSignals(data) {
    let box = document.getElementById('typeSignalsBox');
    if (box) box.remove();
    const rows = [];

    if (data.url_details && data.url_details.host) {
      const d = data.url_details;
      rows.push(`Domain: <strong>${esc(d.host)}</strong>`);
      if (d.brand_match) rows.push(`⚠️ Looks similar to <strong>${esc(d.brand_match)}</strong> — possible lookalike domain`);
      if (d.shortener) rows.push(`🔗 Shortened link — real destination is hidden`);
      if (d.ip_based) rows.push(`⚠️ IP address used instead of a domain name`);
      if (d.tld) rows.push(`Uses a free/high-risk domain ending (${esc(d.tld)})`);
    }
    if (data.network) rows.push(`📶 Number appears to be on the <strong>${esc(data.network)}</strong> network`);
    if (data.community_reports && data.community_reports.length) {
      rows.push(`🚩 Reported ${data.community_reports.length}x by the Veridict community — <a href="/community" style="color:var(--v-purple-lt);font-weight:600">view reports</a>`);
    }
    if (!rows.length) return;

    box = document.createElement('div');
    box.id = 'typeSignalsBox';
    box.style.cssText = 'padding:14px 22px;border-top:1px solid var(--v-border)';
    const label = document.createElement('div');
    label.style.cssText = 'font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--v-muted);margin-bottom:10px';
    label.textContent = 'Scanner findings';
    box.appendChild(label);
    rows.forEach(r => {
      const row = document.createElement('div');
      row.style.cssText = 'font-size:.82rem;color:var(--v-muted);padding-left:20px;position:relative;margin-bottom:8px;line-height:1.5';
      row.innerHTML = `<span style="position:absolute;left:0">•</span>${r}`;
      box.appendChild(row);
    });
    verdictPanel.appendChild(box);
  }

  function renderRecommendedActions(actions) {
    let box = document.getElementById('recommendedActionsBox');
    if (box) box.remove();
    if (!actions || !actions.length) return;

    box = document.createElement('div');
    box.id = 'recommendedActionsBox';
    box.style.cssText = 'padding:14px 22px;border-top:1px solid var(--v-border)';
    const label = document.createElement('div');
    label.style.cssText = 'font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--v-muted);margin-bottom:10px';
    label.textContent = 'What to do next';
    box.appendChild(label);

    actions.forEach(a => {
      const row = document.createElement('div');
      row.style.cssText = 'font-size:.82rem;color:var(--v-muted);padding-left:20px;position:relative;margin-bottom:8px;line-height:1.5';
      row.innerHTML = `<span style="position:absolute;left:0">•</span>${esc(a)}`;
      box.appendChild(row);
    });

    verdictPanel.appendChild(box);
  }

  function riskLevelFromScore(score) {
    if (score >= 80) return 'Critical';
    if (score >= 55) return 'High';
    if (score >= 25) return 'Medium';
    return 'Low';
  }

  function renderHighlightBox(sourceText, highlights) {
    if (!sourceText || !highlights || !highlights.length) { highlightBox.style.display='none'; highlightBox.innerHTML=''; return; }
    let html = esc(sourceText);
    // Longest snippets first so shorter overlapping matches don't fragment a longer one.
    const sorted = [...highlights].sort((a,b) => b.length - a.length);
    sorted.forEach(snippet => {
      if (!snippet) return;
      const escSnippet = esc(snippet);
      if (!escSnippet.trim()) return;
      const pattern = escSnippet.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const re = new RegExp(`(${pattern})`, 'gi');
      html = html.replace(re, (m, g1, offset, str) => {
        // Skip if already inside a <mark> tag from a previous pass.
        const before = str.slice(0, offset);
        const openCount = (before.match(/<mark>/g)||[]).length;
        const closeCount = (before.match(/<\/mark>/g)||[]).length;
        if (openCount > closeCount) return m;
        return `<mark>${m}</mark>`;
      });
    });
    highlightBox.className = 'sc-highlight-box';
    highlightBox.style.display = 'block';
    highlightBox.innerHTML = `<div class="sc-highlight-box__label">Flagged in your text</div><div class="sc-highlight-box__text">${html}</div>`;
  }

  function displayVerdict(data, scroll) {
    const label=data.verdict.charAt(0).toUpperCase()+data.verdict.slice(1);
    verdictBadge.textContent=label; verdictBadge.className=`sc-verdict-badge verdict--${data.verdict}`;
    const riskLevel = data.risk_level || riskLevelFromScore(data.score);
    riskLevelBadge.textContent = riskLevel; riskLevelBadge.className = `sc-risk-badge risk--${riskLevel.toLowerCase()}`;
    verdictScore.textContent=`Risk score: ${data.score}/100`; verdictTime.textContent=data.scanned_at?fmt(data.scanned_at):'';
    flagList.innerHTML=''; flagList.classList.toggle('sc-flag-list--clean', !data.flags?.length);
    (data.flags?.length?data.flags:['No specific red flags detected.']).forEach(f => { const li=document.createElement('li'); li.textContent=f; flagList.appendChild(li); });
    verdictExp.textContent=data.explanation||'';
    if (data.explanation_truncated) {
      verdictExp.innerHTML = data.explanation.replace('Upgrade to Premium', '<a href="/plan" style="color:var(--v-purple-lt);font-weight:600">Upgrade to Premium</a>');
    }
    // Highlight matched snippets against the full text on a fresh scan,
    // or against the stored preview when replaying a history entry.
    const sourceForHighlight = scroll ? lastScannedText : (data.preview || '');
    renderHighlightBox(sourceForHighlight, data.highlights);
    renderRecommendedActions(data.recommended_actions);
    renderTypeSignals(data);
    renderDeepAnalysis(data.deep_analysis);
    verdictPanel.classList.add('is-visible');
    if (scroll) verdictPanel.scrollIntoView({behavior:'smooth',block:'nearest'});
  }

  scanAnotherBtn.addEventListener('click', () => { verdictPanel.classList.remove('is-visible'); scanInput.value=''; charCount.textContent='0 / 5000'; scanInput.focus(); });
  copyResultBtn.addEventListener('click', async () => {
    if (!lastResult) return;
    const txt=[`Veridict — ${TYPES[activeType]?.label||'Scanner'}`,`Verdict: ${lastResult.verdict.toUpperCase()}`,`Risk score: ${lastResult.score}/100`,lastResult.flags?.length?`Signals: ${lastResult.flags.join(', ')}`:'',`— Jyram Labs`].filter(Boolean).join('\n');
    try { await navigator.clipboard.writeText(txt); copyResultBtn.textContent='✓ Copied!'; setTimeout(()=>{copyResultBtn.textContent='Copy result';},1800); } catch { copyResultBtn.textContent='Copy failed'; }
  });

  async function loadStats() {
    try { const r=await fetch('/api/scan/stats',{credentials:'same-origin'}); if(!r.ok)return; const d=await r.json();
      if (d.is_premium) upgradeNudge.classList.remove('is-visible');
      else if ((d.free_scans_remaining??0) <= 0) upgradeNudge.classList.add('is-visible');
    } catch(e){}
  }
  async function loadHistory() {
    try { const r=await fetch('/api/scan/history',{credentials:'same-origin'}); if(!r.ok)return; const d=await r.json(); renderHistory(d.history||[]); } catch(e){}
  }
  function renderHistory(history) {
    historyList.innerHTML='';
    if (!history.length) { historyList.appendChild(historyEmpty); return; }
    history.forEach(entry => {
      const li=document.createElement('li'); li.className='sc-history-item';
      li.innerHTML=`<span class="sc-history-item__preview">${esc(entry.preview)}</span><div class="sc-history-item__meta"><span class="sc-history-item__pill verdict--${entry.verdict}">${entry.verdict}</span><span class="sc-history-item__time">${fmt(entry.scanned_at)}</span></div>`;
      li.addEventListener('click', () => displayVerdict(entry,false));
      historyList.appendChild(li);
    });
  }
  function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
  function fmt(iso){try{return new Date(iso).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});}catch{return'';}}

  // ─── BULK SCANNER (Premium feature) ───
  const bulkInput = document.getElementById('bulkInput');
  const bulkBtn = document.getElementById('bulkScanBtn');
  const bulkError = document.getElementById('bulkError');
  const bulkResults = document.getElementById('bulkResults');

  if (bulkBtn) {
    bulkBtn.addEventListener('click', async () => {
      const lines = bulkInput.value.split('\n').map(l => l.trim()).filter(Boolean);
      if (!lines.length) { bulkError.textContent = 'Paste at least one message.'; bulkError.classList.add('is-visible'); return; }
      if (lines.length > 20) { bulkError.textContent = 'Maximum 20 items at once.'; bulkError.classList.add('is-visible'); return; }
      bulkError.classList.remove('is-visible');
      bulkBtn.classList.add('is-loading'); bulkBtn.disabled = true;
      bulkResults.style.display = 'none';
      try {
        const res = await fetch('/api/scan/bulk', {
          method: 'POST', credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({ items: lines, type: activeType })
        });
        const data = await res.json();
        if (!res.ok) {
          if (data.upgrade_required) {
            bulkResults.style.display = 'block';
            bulkResults.innerHTML = `<div style="padding:14px 16px;border-radius:10px;background:rgba(201,147,46,.1);border:1px solid rgba(201,147,46,.3);font-size:.84rem">${data.message} <a href="/plan" style="color:var(--v-purple-lt);font-weight:600">Upgrade now →</a></div>`;
          } else {
            bulkError.textContent = data.message || 'Could not run bulk scan.';
            bulkError.classList.add('is-visible');
          }
          return;
        }
        renderBulkResults(data.results);
        loadStats(); loadHistory();
      } catch (e) {
        bulkError.textContent = 'Connection error.'; bulkError.classList.add('is-visible');
      } finally {
        bulkBtn.classList.remove('is-loading'); bulkBtn.disabled = false;
      }
    });
  }

  function renderBulkResults(results) {
    bulkResults.style.display = 'block';
    const threats = results.filter(r => r.verdict !== 'safe').length;
    let html = `<p style="font-size:.82rem;color:var(--v-muted);margin-bottom:12px">Scanned ${results.length} items — ${threats} flagged as risky.</p>`;
    results.forEach(r => {
      html += `<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:8px;background:var(--v-input);border:1px solid var(--v-border);margin-bottom:8px">
        <span class="sc-verdict-badge verdict--${r.verdict}" style="font-size:.65rem;padding:3px 10px;flex-shrink:0">${r.verdict}</span>
        <span style="font-size:.8rem;color:var(--v-muted);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(r.preview)}</span>
        <span style="font-size:.74rem;color:var(--v-faint);flex-shrink:0">${r.score}/100</span>
      </div>`;
    });
    bulkResults.innerHTML = html;
  }

  init();
});