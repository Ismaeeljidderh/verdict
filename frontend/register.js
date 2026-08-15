/* =========================================================
   VERIDICT — REGISTER PAGE LOGIC
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {

  const form            = document.getElementById('registerForm');
  const fullNameInput   = document.getElementById('fullName');
  const usernameInput   = document.getElementById('username');
  const emailInput      = document.getElementById('regEmail');
  const passwordInput   = document.getElementById('regPassword');
  const confirmInput    = document.getElementById('confirmPassword');
  const agreeTerms      = document.getElementById('agreeTerms');
  const registerBtn     = document.getElementById('registerBtn');
  const formStatus      = document.getElementById('registerFormStatus');

  const fields = {
    fullName:        { input: fullNameInput, wrap: document.getElementById('fullNameField'),       err: document.getElementById('fullNameError') },
    username:        { input: usernameInput, wrap: document.getElementById('usernameField'),       err: document.getElementById('usernameError') },
    email:           { input: emailInput,    wrap: document.getElementById('regEmailField'),       err: document.getElementById('regEmailError') },
    password:        { input: passwordInput, wrap: document.getElementById('regPasswordField'),    err: document.getElementById('regPasswordError') },
    confirmPassword: { input: confirmInput,  wrap: document.getElementById('confirmPasswordField'),err: document.getElementById('confirmPasswordError') },
  };

  let csrfToken = '';

  /* CSRF -------------------------------------------------- */
  async function loadCsrf() {
    try {
      const r = await fetch('/api/csrf-token', { credentials: 'same-origin' });
      const d = await r.json();
      csrfToken = d.csrf_token || '';
    } catch(e) { console.warn('CSRF fetch failed', e); }
  }
  loadCsrf();

  /* Password toggles -------------------------------------- */
  function wireToggle(id, input) {
    document.getElementById(id).addEventListener('click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      document.getElementById(id).classList.toggle('is-visible', show);
      document.getElementById(id).setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
  }
  wireToggle('regPasswordToggle', passwordInput);
  wireToggle('confirmPasswordToggle', confirmInput);

  /* Validation helpers ------------------------------------ */
  function isValidEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()); }
  function isValidUsername(v) { return /^[a-zA-Z0-9_]{3,20}$/.test(v.trim()); }

  function setErr(key, msg) { fields[key].wrap.classList.add('has-error'); fields[key].err.textContent = msg; }
  function clrErr(key)      { fields[key].wrap.classList.remove('has-error'); fields[key].err.textContent = ''; }

  function showStatus(msg, type) {
    formStatus.textContent = msg;
    formStatus.className = 'form-status ' + (type === 'success' ? 'is-success' : 'is-error');
  }

  function validate() {
    let ok = true;
    if (!fullNameInput.value.trim())          { setErr('fullName', 'Full name is required.');                         ok = false; } else clrErr('fullName');
    if (!isValidUsername(usernameInput.value)){ setErr('username', '3-20 characters: letters, numbers, underscores.'); ok = false; } else clrErr('username');
    if (!isValidEmail(emailInput.value))      { setErr('email',    'Enter a valid email address.');                   ok = false; } else clrErr('email');
    if (passwordInput.value.length < 8)       { setErr('password', 'Password must be at least 8 characters.');       ok = false; } else clrErr('password');
    if (confirmInput.value !== passwordInput.value || !confirmInput.value) { setErr('confirmPassword', 'Passwords do not match.'); ok = false; } else clrErr('confirmPassword');
    if (!agreeTerms.checked) { showStatus('You must agree to the Terms and Privacy Policy.', 'error'); ok = false; }
    return ok;
  }

  Object.keys(fields).forEach(key => {
    fields[key].input.addEventListener('input', () => { if (fields[key].wrap.classList.contains('has-error')) validate(); });
  });

  /* Submit ------------------------------------------------ */
  form.addEventListener('submit', async e => {
    e.preventDefault();
    formStatus.className = 'form-status';
    formStatus.textContent = '';

    if (!validate()) return;

    registerBtn.classList.add('is-loading');
    registerBtn.disabled = true;

    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({
          full_name: fullNameInput.value.trim(),
          username:  usernameInput.value.trim(),
          email:     emailInput.value.trim().toLowerCase(),
          password:  passwordInput.value
        })
      });
      const data = await res.json();
      if (res.ok) {
        showStatus(data.message || 'Account created! Redirecting…', 'success');
        setTimeout(() => { window.location.href = data.redirect || '/dashboard'; }, 900);
      } else {
        showStatus(data.message || 'Could not create account. Please try again.', 'error');
        registerBtn.classList.remove('is-loading');
        registerBtn.disabled = false;
      }
    } catch (err) {
      showStatus('Connection error. Please try again.', 'error');
      registerBtn.classList.remove('is-loading');
      registerBtn.disabled = false;
    }
  });
});
