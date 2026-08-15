/* =========================================================
   VERIDICT — ONBOARDING WELCOME MODAL
   Shows once to new users after their first login.
   Stored in localStorage so it only shows once per browser.
   ========================================================= */
(function () {
  'use strict';

  const STORAGE_KEY = 'veridict_onboarded';

  window.VeriditOnboarding = {
    show(userName) {
      if (localStorage.getItem(STORAGE_KEY)) return;

      const style = document.createElement('style');
      style.textContent = `
        .ob-overlay {
          position:fixed;inset:0;z-index:9998;
          background:rgba(5,6,10,0.9);
          backdrop-filter:blur(14px);
          display:flex;align-items:center;justify-content:center;padding:24px;
          animation:obIn 0.3s ease;
        }
        @keyframes obIn{from{opacity:0}to{opacity:1}}
        .ob-card {
          width:100%;max-width:520px;border-radius:22px;
          background:#0f0f1e;border:1px solid rgba(124,92,252,0.35);
          box-shadow:0 32px 80px rgba(0,0,0,0.6);overflow:hidden;
          animation:obUp 0.35s cubic-bezier(0.16,1,0.3,1);
        }
        @keyframes obUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
        .ob-header {
          background:linear-gradient(135deg,#0d0b20,#0f0f2e);
          padding:40px 36px 28px;text-align:center;position:relative;
          border-bottom:1px solid rgba(124,92,252,0.2);
        }
        .ob-shield {
          width:70px;height:70px;border-radius:18px;margin:0 auto 18px;
          background:linear-gradient(135deg,rgba(124,92,252,0.3),rgba(79,143,255,0.15));
          border:1px solid rgba(124,92,252,0.4);
          display:flex;align-items:center;justify-content:center;font-size:2rem;
          box-shadow:0 0 32px rgba(124,92,252,0.3);
        }
        .ob-header h2{font-family:'Space Grotesk',sans-serif;font-size:1.4rem;font-weight:600;margin:0 0 8px;letter-spacing:-0.01em}
        .ob-header p{font-size:0.86rem;color:rgba(138,143,163,0.9);margin:0;line-height:1.5}
        .ob-steps{padding:28px 36px;display:flex;flex-direction:column;gap:16px}
        .ob-step{display:flex;gap:14px;align-items:flex-start}
        .ob-step__num{
          width:32px;height:32px;border-radius:50%;flex-shrink:0;
          background:linear-gradient(135deg,#7c5cfc,#4f8fff);
          display:flex;align-items:center;justify-content:center;
          font-family:'Space Grotesk',sans-serif;font-weight:600;color:#fff;font-size:0.85rem;
          box-shadow:0 4px 12px rgba(124,92,252,0.35);
        }
        .ob-step__text h4{font-family:'Space Grotesk',sans-serif;font-size:0.9rem;font-weight:600;margin:0 0 3px}
        .ob-step__text p{font-size:0.78rem;color:rgba(138,143,163,0.8);margin:0;line-height:1.5}
        .ob-footer{padding:0 36px 32px}
        .ob-btn{
          width:100%;padding:14px;border-radius:12px;border:none;
          background:linear-gradient(135deg,#7c5cfc,#4f8fff);color:#fff;
          font-family:'Inter',sans-serif;font-size:0.95rem;font-weight:600;
          cursor:pointer;box-shadow:0 8px 24px rgba(124,92,252,0.35);
          transition:filter 0.18s,transform 0.18s;
        }
        .ob-btn:hover{filter:brightness(1.08);transform:translateY(-1px)}
        .ob-free-note{text-align:center;font-size:0.75rem;color:rgba(138,143,163,0.6);margin-top:10px}
      `;
      document.head.appendChild(style);

      const name = userName || 'there';
      const overlay = document.createElement('div');
      overlay.className = 'ob-overlay';
      overlay.innerHTML = `
        <div class="ob-card">
          <div class="ob-header">
            <div class="ob-shield">🛡️</div>
            <h2>Welcome to Veridict, ${name}!</h2>
            <p>You're now protected by AI-powered scam detection. Here's how to get started:</p>
          </div>
          <div class="ob-steps">
            <div class="ob-step">
              <div class="ob-step__num">1</div>
              <div class="ob-step__text">
                <h4>Run your first scan</h4>
                <p>Click Scanner in the sidebar and paste any suspicious message, link, or email.</p>
              </div>
            </div>
            <div class="ob-step">
              <div class="ob-step__num">2</div>
              <div class="ob-step__text">
                <h4>Get an instant verdict</h4>
                <p>Veridict checks 30+ scam signals and returns Safe, Suspicious, or Scam in under 3 seconds.</p>
              </div>
            </div>
            <div class="ob-step">
              <div class="ob-step__num">3</div>
              <div class="ob-step__text">
                <h4>Track your threats</h4>
                <p>All your scans are saved in Scam Alerts so you can review them any time.</p>
              </div>
            </div>
            <div class="ob-step">
              <div class="ob-step__num">4</div>
              <div class="ob-step__text">
                <h4>Need more scans?</h4>
                <p>Watch a short ad for 3 bonus scans, or upgrade to Premium for unlimited.</p>
              </div>
            </div>
          </div>
          <div class="ob-footer">
            <button class="ob-btn" id="obDismiss">Let's go — start scanning 🛡️</button>
            <p class="ob-free-note">You have 10 free scans this week · No card required</p>
          </div>
        </div>`;

      document.body.appendChild(overlay);

      document.getElementById('obDismiss').addEventListener('click', () => {
        localStorage.setItem(STORAGE_KEY, '1');
        overlay.style.animation = 'obIn 0.2s ease reverse';
        setTimeout(() => overlay.remove(), 200);
        // Navigate to scanner for first action
        window.location.href = '/scanner';
      });
    }
  };
})();
