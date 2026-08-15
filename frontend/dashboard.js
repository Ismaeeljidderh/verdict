/* =========================================================
   VERIDICT — DASHBOARD.JS
   Populates all dynamic data to match the reference design:
   greeting, stat cards, donut ring, risk chart, recent alerts,
   plan card, upgrade banner, email verify banner.
   ========================================================= */
'use strict';

document.addEventListener('DOMContentLoaded', async () => {

  let csrfToken = '';

  /* ── CSRF ── */
  try {
    const r = await fetch('/api/csrf-token', { credentials: 'same-origin' });
    csrfToken = (await r.json()).csrf_token || '';
    if (window.VeridictAd) window.VeridictAd.init(csrfToken);
  } catch(e) {}

  /* ── Load user + stats in parallel ── */
  try {
    const [meRes, statsRes, histRes] = await Promise.all([
      fetch('/api/me',           { credentials: 'same-origin' }),
      fetch('/api/scan/stats',   { credentials: 'same-origin' }),
      fetch('/api/scan/history?limit=4', { credentials: 'same-origin' }),
    ]);

    if (meRes.status === 401) { window.location.href = '/login'; return; }

    const me    = await meRes.json();
    const stats = statsRes.ok ? await statsRes.json() : {};
    const hist  = histRes.ok  ? await histRes.json()  : {};

    renderUser(me);
    renderStats(stats);
    renderRisk(stats);
    renderRecentAlerts(hist.history || []);
    renderPlanCard(me, stats);
    checkVerifyBanner(me, csrfToken);

    /* Onboarding for brand new users */
    if ((stats.total_scans || 0) === 0 && window.VeriditOnboarding) {
      const firstName = (me.full_name || '').split(' ')[0] || me.username || 'there';
      setTimeout(() => window.VeriditOnboarding.show(firstName), 900);
    }

  } catch(e) {
    console.error('Dashboard load error:', e);
  }

  /* ──────────────────────────────────────────────
     RENDER USER
  ────────────────────────────────────────────── */
  function renderUser(me) {
    const name    = me.full_name || me.username || 'User';
    const initial = name.charAt(0).toUpperCase();
    const first   = name.split(' ')[0];

    document.getElementById('dbGreeting').textContent    = `Welcome back, ${first}! 👋`;
    document.getElementById('topbarAvatar').textContent  = initial;
    document.getElementById('topbarName').textContent    = name;

    const badge = document.getElementById('topbarBadge');
    if (me.is_premium) {
      badge.textContent = 'PRO';
      badge.style.background = 'linear-gradient(135deg,#6d28d9,#8b5cf6)';
    } else {
      badge.textContent = 'FREE';
      badge.style.background = 'rgba(255,255,255,0.1)';
    }
  }

  /* ──────────────────────────────────────────────
     RENDER STAT CARDS
  ────────────────────────────────────────────── */
  function renderStats(stats) {
    const total     = stats.total_scans          || 0;
    const threats   = stats.threats_blocked      || 0;
    const remaining = stats.free_scans_remaining;
    const isPremium = stats.is_premium;

    /* Total scans */
    document.getElementById('statTotal').textContent    = total.toLocaleString();
    document.getElementById('statTotalSub').textContent = `↑ ${total} all time`;

    /* Threats */
    document.getElementById('statThreats').textContent    = threats.toLocaleString();
    document.getElementById('statThreatsSub').textContent = `${threats} blocked`;

    /* Scans left + donut ring */
    if (isPremium) {
      document.getElementById('statLeft').textContent   = '∞';
      document.getElementById('statLeftSub').textContent = 'Unlimited — Premium';
      setDonut(100);
    } else {
      const used = Math.max(0, 10 - (remaining || 0));
      document.getElementById('statLeft').textContent    = `${remaining ?? 0} / 10`;
      document.getElementById('statLeftSub').textContent = 'Resets every week';
      setDonut(((remaining ?? 0) / 10) * 100);

      if ((remaining ?? 1) <= 0) {
        document.getElementById('upgradeBanner').style.display = 'flex';
      }
    }

    /* Account plan card */
    document.getElementById('statPlanName').textContent = isPremium ? 'Premium Plan' : 'Free Plan';
    document.getElementById('statPlanSub').textContent  = isPremium ? 'Unlimited scans active ✓' : 'Upgrade for unlimited scans';
    if (isPremium) {
      document.getElementById('statPlanName').style.color = '#22c55e';
    }
  }

  function setDonut(pct) {
    const ring = document.getElementById('donutRing');
    if (!ring) return;
    const circ  = 2 * Math.PI * 22; // r=22
    const dash  = (pct / 100) * circ;
    ring.style.strokeDasharray  = `${dash} ${circ}`;
    ring.style.strokeDashoffset = '0';
  }

  /* ──────────────────────────────────────────────
     RENDER RISK DONUT CHART
  ────────────────────────────────────────────── */
  function renderRisk(stats) {
    const total   = stats.threats_blocked || 0;
    const high    = Math.round(total * 0.5);
    const medium  = Math.round(total * 0.33);
    const low     = Math.max(0, total - high - medium);
    const circ    = 2 * Math.PI * 38; // r=38, circumference ≈ 238.76

    document.getElementById('riskTotal').textContent     = total;
    document.getElementById('riskHighCount').textContent = `${high} (${total ? Math.round(high/total*100) : 0}%)`;
    document.getElementById('riskMedCount').textContent  = `${medium} (${total ? Math.round(medium/total*100) : 0}%)`;
    document.getElementById('riskLowCount').textContent  = `${low} (${total ? Math.round(low/total*100) : 0}%)`;

    if (total === 0) return;

    const highPct   = high   / total;
    const medPct    = medium / total;
    const lowPct    = low    / total;

    const highDash  = highPct  * circ;
    const medDash   = medPct   * circ;
    const lowDash   = lowPct   * circ;

    const highOffset = 0;
    const medOffset  = -(highDash);
    const lowOffset  = -(highDash + medDash);

    const rHigh = document.getElementById('riskHigh');
    const rMed  = document.getElementById('riskMed');
    const rLow  = document.getElementById('riskLow');

    rHigh.style.strokeDasharray  = `${highDash} ${circ - highDash}`;
    rHigh.style.strokeDashoffset = String(highOffset);
    rMed.style.strokeDasharray   = `${medDash} ${circ - medDash}`;
    rMed.style.strokeDashoffset  = String(medOffset);
    rLow.style.strokeDasharray   = `${lowDash} ${circ - lowDash}`;
    rLow.style.strokeDashoffset  = String(lowOffset);
  }

  /* ──────────────────────────────────────────────
     RENDER RECENT ALERTS
  ────────────────────────────────────────────── */
  function renderRecentAlerts(history) {
    const el = document.getElementById('recentAlertsList');
    if (!el) return;

    const threats = history.filter(h => h.verdict !== 'safe').slice(0, 4);
    if (!threats.length) {
      el.innerHTML = '<div style="font-size:0.78rem;color:var(--db-faint);text-align:center;padding:16px">No threats detected yet. Keep scanning!</div>';
      return;
    }

    const TYPE_ICONS = { message:'💬', website:'🌐', email:'📧', phone:'📞', screenshot:'📷', qr:'🔲' };
    const STATUS = {
      scam:       { text: 'Scam detected',     cls: 'db-alert-item__status--scam' },
      suspicious: { text: 'Potentially Unsafe', cls: 'db-alert-item__status--warn' },
    };

    el.innerHTML = threats.map(h => {
      const icon = TYPE_ICONS[h.type] || '⚠️';
      const s    = STATUS[h.verdict] || STATUS.scam;
      const ago  = timeAgo(h.scanned_at);
      return `
        <div class="db-alert-item">
          <div class="db-alert-item__icon">${icon}</div>
          <div class="db-alert-item__body">
            <div class="db-alert-item__title">${esc(h.preview)}</div>
            <div class="db-alert-item__status ${s.cls}">${s.text}</div>
          </div>
          <div class="db-alert-item__time">${ago}</div>
        </div>`;
    }).join('');

    /* Show notification dot if any threats */
    if (threats.length) {
      const dot = document.getElementById('notifDot');
      if (dot) dot.style.display = 'block';
    }
  }

  /* ──────────────────────────────────────────────
     RENDER PLAN CARD (sidebar bottom)
  ────────────────────────────────────────────── */
  function renderPlanCard(me, stats) {
    const isPremium = me.is_premium;
    const remaining = stats.free_scans_remaining ?? 10;
    const used      = Math.max(0, 10 - remaining);
    const pct       = isPremium ? 100 : (remaining / 10) * 100;

    document.getElementById('planCardName').textContent = isPremium ? 'Premium Plan ✓' : 'Free Plan';
    document.getElementById('planCardScans').textContent = isPremium ? '∞ / ∞' : `${remaining} / 10`;
    document.getElementById('planCardBar').style.width   = pct + '%';

    if (isPremium) {
      document.getElementById('planCardBar').style.background = 'linear-gradient(90deg,#22c55e,#4ade80)';
    }
  }

  /* ──────────────────────────────────────────────
     EMAIL VERIFICATION BANNER
  ────────────────────────────────────────────── */
  function checkVerifyBanner(me, csrf) {
    if (me.email_verified || me.has_google) return;
    const banner = document.getElementById('verifyBanner');
    if (banner) banner.style.display = 'flex';

    const btn = document.getElementById('resendVerifyBtn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      btn.textContent = 'Sending…'; btn.disabled = true;
      try {
        await fetch('/api/resend-verification', { method:'POST', credentials:'same-origin', headers:{'X-CSRFToken':csrf} });
        btn.textContent = '✓ Sent!';
        setTimeout(() => { btn.textContent = 'Resend email'; btn.disabled = false; }, 3000);
      } catch { btn.textContent = 'Error'; btn.disabled = false; }
    });
  }

  /* ──────────────────────────────────────────────
     WATCH AD BUTTON
  ────────────────────────────────────────────── */
  document.getElementById('watchAdBtn')?.addEventListener('click', () => {
    if (window.VeridictAd) {
      window.VeridictAd.show(reward => {
        document.getElementById('upgradeBanner').style.display = 'none';
        const scansEl = document.getElementById('statLeft');
        if (scansEl && scansEl.textContent !== '∞') {
          const parts = scansEl.textContent.split('/');
          if (parts.length === 2) {
            const newLeft = parseInt(parts[0].trim()) + reward.bonus_granted;
            scansEl.textContent = `${newLeft} / 10`;
          }
        }
      });
    }
  });

  /* ──────────────────────────────────────────────
     LOGOUT
  ────────────────────────────────────────────── */
  document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    try {
      await fetch('/api/logout', { method:'POST', credentials:'same-origin', headers:{'X-CSRFToken':csrfToken} });
    } finally {
      window.location.href = '/';
    }
  });

  /* ──────────────────────────────────────────────
     HELPERS
  ────────────────────────────────────────────── */
  function timeAgo(iso) {
    try {
      const m = Math.floor((Date.now() - new Date(iso)) / 60000);
      if (m < 1)  return 'just now';
      if (m < 60) return m + 'm ago';
      const h = Math.floor(m / 60);
      if (h < 24) return h + 'h ago';
      return Math.floor(h / 24) + 'd ago';
    } catch { return ''; }
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = String(s || '').slice(0, 32) + (String(s || '').length > 32 ? '…' : '');
    return d.innerHTML;
  }

});