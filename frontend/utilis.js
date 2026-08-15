(function () {
  'use strict';
  const BONUS = 3, DURATION = 15;
  let showing = false;
  const CSS = `.rad-overlay{position:fixed;inset:0;z-index:9999;background:rgba(5,6,10,.9);backdrop-filter:blur(14px);display:flex;align-items:center;justify-content:center;padding:24px;animation:radFade .25s ease}
@keyframes radFade{from{opacity:0}to{opacity:1}}
.rad-card{width:100%;max-width:430px;border-radius:20px;background:#0e0e1c;border:1px solid rgba(124,92,252,.35);box-shadow:0 32px 80px rgba(0,0,0,.6);overflow:hidden;animation:radUp .3s cubic-bezier(.16,1,.3,1)}
@keyframes radUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.rad-screen{background:linear-gradient(135deg,#0d0b20,#0f0f2e);padding:38px 30px 28px;text-align:center;position:relative;min-height:200px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
.rad-timer{position:absolute;top:12px;right:14px;font-size:.74rem;color:rgba(138,143,163,.7)}
.rad-icon{width:68px;height:68px;border-radius:16px;background:rgba(124,92,252,.2);border:1px solid rgba(124,92,252,.35);display:flex;align-items:center;justify-content:center;font-size:1.9rem;margin:0 auto;box-shadow:0 0 28px rgba(124,92,252,.3)}
.rad-label{font-size:.62rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:rgba(138,143,163,.6)}
.rad-title{font-family:'Space Grotesk',sans-serif;font-size:1.05rem;font-weight:600;color:#e8e9f0;margin:0}
.rad-sub{font-size:.8rem;color:rgba(138,143,163,.85);margin:0}
.rad-bar{width:100%;height:3px;border-radius:2px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:6px}
.rad-bar__fill{height:100%;width:0;border-radius:2px;background:linear-gradient(90deg,#7c5cfc,#7ba3bd);transition:width 1s linear}
.rad-body{padding:22px 26px 26px}
.rad-reward{display:flex;align-items:center;gap:12px;padding:13px 15px;border-radius:11px;background:rgba(124,92,252,.1);border:1px solid rgba(124,92,252,.25);margin-bottom:16px}
.rad-reward__icon{font-size:1.3rem}
.rad-reward__text h4{font-family:'Space Grotesk',sans-serif;font-size:.88rem;font-weight:600;margin:0 0 2px}
.rad-reward__text p{font-size:.76rem;color:rgba(138,143,163,.85);margin:0}
.rad-btn{width:100%;padding:13px;border-radius:10px;border:none;font-family:'Inter',sans-serif;font-size:.9rem;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;transition:all .18s}
.rad-btn--primary{background:linear-gradient(135deg,#7c5cfc,#7ba3bd);color:#fff;box-shadow:0 8px 24px rgba(124,92,252,.35)}
.rad-btn--primary:hover{filter:brightness(1.08);transform:translateY(-1px)}
.rad-btn--primary:disabled{opacity:.5;cursor:not-allowed;transform:none}
.rad-btn--skip{background:transparent;color:rgba(138,143,163,.7);font-size:.76rem;padding:8px;font-weight:400;margin-top:8px}
.rad-btn--skip:hover{color:#e8e9f0}
.rad-spin{width:15px;height:15px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:rSpin .7s linear infinite;display:none}
.rad-btn.is-loading .rad-btn__label{display:none}.rad-btn.is-loading .rad-spin{display:block}
@keyframes rSpin{to{transform:rotate(360deg)}}
.rad-status{font-size:.76rem;text-align:center;margin-top:9px;min-height:16px}
.rad-status.ok{color:#34d399}.rad-status.err{color:#ff5c72}`;

  function injectCSS() { if (document.getElementById('rad-css')) return; const s=document.createElement('style'); s.id='rad-css'; s.textContent=CSS; document.head.appendChild(s); }

  function buildModal(csrfToken, onRewarded) {
    injectCSS();
    const ov = document.createElement('div'); ov.className='rad-overlay'; ov.id='radOverlay';
    ov.innerHTML = `<div class="rad-card"><div class="rad-screen"><span class="rad-timer" id="radTimer">${DURATION}s</span><div class="rad-icon"><svg width="26" height="26" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="16" height="11" rx="1"/><path d="M7 18h6M10 15v3"/></svg></div><p class="rad-label">Advertisement</p><p class="rad-title">Watch &amp; Earn Free Scans</p><p class="rad-sub">Earn ${BONUS} bonus scans by watching this short ad.</p><div class="rad-bar"><div class="rad-bar__fill" id="radFill"></div></div></div><div class="rad-body"><div class="rad-reward"><span class="rad-reward__icon"></span><div class="rad-reward__text"><h4>You'll earn ${BONUS} free scans</h4><p>Watch the full ad — reward unlocks automatically.</p></div></div><button class="rad-btn rad-btn--primary" id="radClaim" disabled><span class="rad-btn__label" id="radClaimLabel">Ad playing… (${DURATION}s)</span><span class="rad-spin"></span></button><button class="rad-btn rad-btn--skip" id="radSkip">No thanks, maybe later</button><p class="rad-status" id="radStatus"></p></div></div>`;
    document.body.appendChild(ov);
    const claim=document.getElementById('radClaim'), label=document.getElementById('radClaimLabel'), skip=document.getElementById('radSkip'), timer=document.getElementById('radTimer'), fill=document.getElementById('radFill'), stat=document.getElementById('radStatus');
    let left = DURATION;
    const tick = setInterval(() => {
      left--; timer.textContent = left+'s'; fill.style.width = ((DURATION-left)/DURATION*100)+'%';
      if (left <= 0) { clearInterval(tick); timer.textContent='✓ Done'; claim.disabled=false; label.textContent=`Claim ${BONUS} free scans`; }
      else label.textContent = `Ad playing… (${left}s)`;
    }, 1000);
    claim.addEventListener('click', async () => {
      claim.classList.add('is-loading'); claim.disabled=true; skip.hidden=true;
      try {
        const res = await fetch('/api/scan/reward-ad', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({ad_token:'dev-'+Date.now()})});
        const d = await res.json();
        if (res.ok) { stat.textContent=d.message; stat.className='rad-status ok'; setTimeout(()=>{closeModal(); if(typeof onRewarded==='function')onRewarded(d);},1400); }
        else { stat.textContent=d.message||'Could not grant reward.'; stat.className='rad-status err'; claim.classList.remove('is-loading'); claim.disabled=false; skip.hidden=false; }
      } catch { stat.textContent='Connection error.'; stat.className='rad-status err'; claim.classList.remove('is-loading'); claim.disabled=false; skip.hidden=false; }
    });
    skip.addEventListener('click', () => { clearInterval(tick); closeModal(); });
  }
  function closeModal() { const ov=document.getElementById('radOverlay'); if(!ov)return; ov.style.animation='radFade .2s ease reverse'; setTimeout(()=>{ov.remove();showing=false;},200); }
  window.VeridictAd = { init(t){window._vcToken=t;}, show(cb){ if(showing)return; showing=true; buildModal(window._vcToken||'',cb); } };
})();

(function () {
  'use strict';
  const KEY = 'veridict_onboarded';
  const CSS = `.ob-overlay{position:fixed;inset:0;z-index:9998;background:rgba(5,6,10,.92);backdrop-filter:blur(14px);display:flex;align-items:center;justify-content:center;padding:24px;animation:obFade .3s ease}
@keyframes obFade{from{opacity:0}to{opacity:1}}
.ob-card{width:100%;max-width:500px;border-radius:22px;background:#0e0e1c;border:1px solid rgba(124,92,252,.35);box-shadow:0 32px 80px rgba(0,0,0,.6);overflow:hidden;animation:obUp .35s cubic-bezier(.16,1,.3,1)}
@keyframes obUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
.ob-header{background:linear-gradient(135deg,#0d0b20,#0f0f2e);padding:36px 32px 26px;text-align:center;border-bottom:1px solid rgba(124,92,252,.18)}
.ob-shield{width:66px;height:66px;border-radius:16px;margin:0 auto 16px;background:rgba(124,92,252,.2);border:1px solid rgba(124,92,252,.35);display:flex;align-items:center;justify-content:center;font-size:1.9rem;box-shadow:0 0 28px rgba(124,92,252,.3)}
.ob-header h2{font-family:'Space Grotesk',sans-serif;font-size:1.35rem;font-weight:600;margin:0 0 8px;letter-spacing:-.01em}
.ob-header p{font-size:.84rem;color:rgba(138,143,163,.9);margin:0;line-height:1.5}
.ob-steps{padding:26px 30px;display:flex;flex-direction:column;gap:15px}
.ob-step{display:flex;gap:13px;align-items:flex-start}
.ob-num{width:30px;height:30px;border-radius:50%;flex-shrink:0;background:linear-gradient(135deg,#7c5cfc,#7ba3bd);display:flex;align-items:center;justify-content:center;font-family:'Space Grotesk',sans-serif;font-weight:600;color:#fff;font-size:.82rem;box-shadow:0 4px 12px rgba(124,92,252,.35)}
.ob-step h4{font-family:'Space Grotesk',sans-serif;font-size:.88rem;font-weight:600;margin:0 0 3px}
.ob-step p{font-size:.77rem;color:rgba(138,143,163,.85);margin:0;line-height:1.5}
.ob-footer{padding:0 30px 28px}
.ob-btn{width:100%;padding:13px;border-radius:12px;border:none;background:linear-gradient(135deg,#7c5cfc,#7ba3bd);color:#fff;font-family:'Inter',sans-serif;font-size:.92rem;font-weight:600;cursor:pointer;box-shadow:0 8px 24px rgba(124,92,252,.35);transition:filter .18s,transform .18s}
.ob-btn:hover{filter:brightness(1.08);transform:translateY(-1px)}
.ob-note{text-align:center;font-size:.72rem;color:rgba(138,143,163,.55);margin-top:9px}`;
  window.VeriditOnboarding = {
    show(userName) {
      if (localStorage.getItem(KEY)) return;
      if (!document.getElementById('ob-css')) { const s=document.createElement('style'); s.id='ob-css'; s.textContent=CSS; document.head.appendChild(s); }
      const name = userName || 'there';
      const ov = document.createElement('div'); ov.className='ob-overlay';
      ov.innerHTML = `<div class="ob-card"><div class="ob-header"><div class="ob-shield"><svg width="26" height="26" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 2l7 3v5c0 4-3 7-7 8-4-1-7-4-7-8V5l7-3z"/></svg></div><h2>Welcome to Veridict, ${name}!</h2><p>You're now protected by AI-powered scam detection. Here's how to get started:</p></div><div class="ob-steps"><div class="ob-step"><div class="ob-num">1</div><div><h4>Run your first scan</h4><p>Click Scanner in the sidebar and paste any suspicious message, link, or email.</p></div></div><div class="ob-step"><div class="ob-num">2</div><div><h4>Get an instant verdict</h4><p>Veridict checks 30+ scam signals and returns Safe, Suspicious, or Scam in under 3 seconds.</p></div></div><div class="ob-step"><div class="ob-num">3</div><div><h4>Check businesses &amp; URLs</h4><p>Use the Business Checker and URL Analyzer to verify companies and links before engaging.</p></div></div><div class="ob-step"><div class="ob-num">4</div><div><h4>Need more scans?</h4><p>Watch a short ad for 3 bonus scans, or upgrade to Premium for unlimited.</p></div></div></div><div class="ob-footer"><button class="ob-btn" id="obDismiss">Let's go — start scanning <svg width="26" height="26" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 2l7 3v5c0 4-3 7-7 8-4-1-7-4-7-8V5l7-3z"/></svg></button><p class="ob-note">5 free scans every week · No card required</p></div></div>`;
      document.body.appendChild(ov);
      document.getElementById('obDismiss').addEventListener('click', () => { localStorage.setItem(KEY,'1'); ov.style.animation='obFade .2s ease reverse'; setTimeout(()=>{ov.remove(); window.location.href='/scanner';},200); });
    }
  };
})();