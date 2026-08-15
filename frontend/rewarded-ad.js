/* =========================================================
   VERIDICT — REWARDED AD SYSTEM
   Shows a rewarded ad modal when a free user hits their scan
   limit. After the countdown the reward is sent to the server.

   HOW TO WIRE A REAL AD NETWORK:
   ─────────────────────────────────────────────────────────
   Google AdSense Rewarded Ads:
     1. Sign up at google.com/adsense
     2. Create a "Rewarded" ad unit for Web
     3. Replace simulateAdPlayback() with the AdSense JS SDK call
     4. On the "rewarded" callback, use the ad's reward token
        (sent by Google) instead of the simulated one below

   Meta Audience Network (Web):
     1. Sign up at business.facebook.com
     2. Create a Web Rewarded Interstitial placement
     3. Replace simulateAdPlayback() with the Meta SDK call
     4. Use the Meta-generated reward token in the POST body

   Both networks pay out in USD, work in Nigeria, and
   require your site to be live (not localhost).
   ========================================================= */

(function () {
  'use strict';

  const BONUS_SCANS = 3;
  const AD_DURATION = 15; // seconds the simulated ad plays
  let csrfToken = '';
  let isShowing = false;

  /* ---- Inject CSS ---- */
  const style = document.createElement('style');
  style.textContent = `
    .rad-overlay {
      position: fixed; inset: 0; z-index: 9999;
      background: rgba(5,6,10,0.88);
      backdrop-filter: blur(12px);
      display: flex; align-items: center; justify-content: center;
      padding: 24px;
      animation: radFadeIn 0.25s ease;
    }
    @keyframes radFadeIn { from{opacity:0} to{opacity:1} }

    .rad-card {
      width: 100%; max-width: 440px;
      border-radius: 20px;
      background: #0f0f1e;
      border: 1px solid rgba(124,92,252,0.35);
      box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(124,92,252,0.1);
      overflow: hidden;
      animation: radSlideUp 0.3s cubic-bezier(0.16,1,0.3,1);
    }
    @keyframes radSlideUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }

    .rad-ad-screen {
      background: linear-gradient(135deg,#0d0b20,#0f0f2e,#0a0a18);
      padding: 40px 32px 32px;
      text-align: center;
      position: relative;
      min-height: 220px;
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px;
    }

    .rad-ad-icon {
      width: 72px; height: 72px; border-radius: 18px;
      background: linear-gradient(135deg,rgba(124,92,252,0.25),rgba(79,143,255,0.15));
      border: 1px solid rgba(124,92,252,0.35);
      display: flex; align-items: center; justify-content: center;
      font-size: 2rem; margin: 0 auto;
      box-shadow: 0 0 32px rgba(124,92,252,0.3);
    }

    .rad-ad-label {
      font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
      text-transform: uppercase; color: rgba(138,143,163,0.6);
    }

    .rad-ad-title {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.1rem; font-weight: 600; color: #e8e9f0;
      margin: 0;
    }

    .rad-ad-sub { font-size: 0.82rem; color: rgba(138,143,163,0.8); margin: 0; }

    .rad-progress-bar {
      width: 100%; height: 3px; border-radius: 2px;
      background: rgba(255,255,255,0.08); overflow: hidden; margin-top: 8px;
    }
    .rad-progress-bar__fill {
      height: 100%; width: 0%; border-radius: 2px;
      background: linear-gradient(90deg,#7c5cfc,#4f8fff);
      transition: width 1s linear;
    }

    .rad-timer {
      position: absolute; top: 14px; right: 16px;
      font-size: 0.75rem; color: rgba(138,143,163,0.7);
      font-variant-numeric: tabular-nums;
    }

    .rad-body { padding: 24px 28px 28px; }

    .rad-reward-row {
      display: flex; align-items: center; gap: 12px;
      padding: 14px 16px; border-radius: 12px;
      background: rgba(124,92,252,0.1); border: 1px solid rgba(124,92,252,0.25);
      margin-bottom: 18px;
    }
    .rad-reward-icon { font-size: 1.4rem; }
    .rad-reward-text h4 { font-family:'Space Grotesk',sans-serif; font-size:0.92rem; font-weight:600; margin:0 0 2px; }
    .rad-reward-text p  { font-size:0.78rem; color:rgba(138,143,163,0.8); margin:0; }

    .rad-btn {
      width: 100%; padding: 13px 20px;
      border-radius: 10px; border: none;
      font-family: 'Inter', sans-serif; font-size: 0.92rem; font-weight: 600;
      cursor: pointer; transition: all 0.18s;
      display: flex; align-items: center; justify-content: center; gap: 8px;
    }
    .rad-btn--primary {
      background: linear-gradient(135deg,#7c5cfc,#4f8fff);
      color: #fff; box-shadow: 0 8px 24px rgba(124,92,252,0.35);
    }
    .rad-btn--primary:hover { filter: brightness(1.08); transform: translateY(-1px); }
    .rad-btn--primary:disabled { opacity:0.5; cursor:not-allowed; transform:none; }

    .rad-btn--skip {
      background: transparent; color: rgba(138,143,163,0.7);
      font-size: 0.78rem; padding: 8px; margin-top: 8px;
      font-weight: 400;
    }
    .rad-btn--skip:hover { color: #e8e9f0; }

    .rad-spinner {
      width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3);
      border-top-color: #fff; border-radius: 50%;
      animation: radSpin 0.7s linear infinite; display: none;
    }
    .rad-btn.is-loading .rad-btn__label { display:none; }
    .rad-btn.is-loading .rad-spinner   { display:block; }
    @keyframes radSpin { to { transform:rotate(360deg); } }

    .rad-status { font-size:0.78rem; text-align:center; margin-top:10px; min-height:18px; }
    .rad-status.success { color:#34d399; }
    .rad-status.error   { color:#ff5c72; }
  `;
  document.head.appendChild(style);

  /* ---- Public API ---- */
  window.VeridictAd = {
    init(token) { csrfToken = token || ''; },

    /**
     * Show the rewarded ad modal.
     * @param {function} onRewarded - called when reward is granted
     */
    show(onRewarded) {
      if (isShowing) return;
      isShowing = true;
      buildModal(onRewarded);
    },
  };

  /* ---- Build modal ---- */
  function buildModal(onRewarded) {
    const overlay = document.createElement('div');
    overlay.className = 'rad-overlay';
    overlay.id = 'radOverlay';

    overlay.innerHTML = `
      <div class="rad-card">
        <div class="rad-ad-screen" id="radAdScreen">
          <div class="rad-timer" id="radTimer">${AD_DURATION}s</div>
          <div class="rad-ad-icon">📺</div>
          <p class="rad-ad-label">Advertisement</p>
          <p class="rad-ad-title" id="radAdTitle">Watch & Earn Free Scans</p>
          <p class="rad-ad-sub">Earn ${BONUS_SCANS} extra scans by watching this short ad.</p>
          <div class="rad-progress-bar">
            <div class="rad-progress-bar__fill" id="radProgressFill"></div>
          </div>
        </div>

        <div class="rad-body">
          <div class="rad-reward-row">
            <span class="rad-reward-icon">⚡</span>
            <div class="rad-reward-text">
              <h4>You'll earn ${BONUS_SCANS} free scans</h4>
              <p>Watch the full ad — the reward button unlocks automatically.</p>
            </div>
          </div>

          <button class="rad-btn rad-btn--primary" id="radClaimBtn" disabled>
            <span class="rad-btn__label" id="radClaimLabel">Ad playing… (${AD_DURATION}s)</span>
            <span class="rad-spinner"></span>
          </button>
          <button class="rad-btn rad-btn--skip" id="radSkipBtn">No thanks, maybe later</button>

          <p class="rad-status" id="radStatus"></p>
        </div>
      </div>`;

    document.body.appendChild(overlay);

    const claimBtn   = document.getElementById('radClaimBtn');
    const claimLabel = document.getElementById('radClaimLabel');
    const skipBtn    = document.getElementById('radSkipBtn');
    const timerEl    = document.getElementById('radTimer');
    const fillEl     = document.getElementById('radProgressFill');
    const statusEl   = document.getElementById('radStatus');

    /* ---- Start simulated ad countdown ---- */
    let secondsLeft = AD_DURATION;
    const tick = setInterval(() => {
      secondsLeft--;
      timerEl.textContent = secondsLeft + 's';
      fillEl.style.width  = ((AD_DURATION - secondsLeft) / AD_DURATION * 100) + '%';

      if (secondsLeft <= 0) {
        clearInterval(tick);
        timerEl.textContent  = '✓ Done';
        claimBtn.disabled    = false;
        claimLabel.textContent = `Claim ${BONUS_SCANS} free scans`;
      } else {
        claimLabel.textContent = `Ad playing… (${secondsLeft}s)`;
      }
    }, 1000);

    /* ---- Claim reward ---- */
    claimBtn.addEventListener('click', async () => {
      claimBtn.classList.add('is-loading');
      claimBtn.disabled = true;
      skipBtn.hidden    = true;

      // In production: replace 'dev-ad-token' with the real token
      // from your ad network's rewarded callback
      const adToken = 'dev-ad-token-' + Date.now();

      try {
        const res = await fetch('/api/scan/reward-ad', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({ ad_token: adToken })
        });
        const data = await res.json();

        if (res.ok) {
          statusEl.textContent = data.message;
          statusEl.className   = 'rad-status success';
          setTimeout(() => {
            closeModal();
            if (typeof onRewarded === 'function') onRewarded(data);
          }, 1400);
        } else {
          statusEl.textContent = data.message || 'Could not grant reward. Please try again.';
          statusEl.className   = 'rad-status error';
          claimBtn.classList.remove('is-loading');
          claimBtn.disabled = false;
          skipBtn.hidden    = false;
        }
      } catch (err) {
        statusEl.textContent = 'Connection error. Please try again.';
        statusEl.className   = 'rad-status error';
        claimBtn.classList.remove('is-loading');
        claimBtn.disabled = false;
        skipBtn.hidden    = false;
      }
    });

    /* ---- Skip ---- */
    skipBtn.addEventListener('click', () => {
      clearInterval(tick);
      closeModal();
    });
  }

  function closeModal() {
    const overlay = document.getElementById('radOverlay');
    if (overlay) {
      overlay.style.animation = 'radFadeIn 0.2s ease reverse';
      setTimeout(() => {
        overlay.remove();
        isShowing = false;
      }, 200);
    }
  }

})();
