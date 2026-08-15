/* =========================================================
   VERIDICT — LOGIN PAGE LOGIC
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {

  const loginForm       = document.getElementById('loginForm');
  const emailInput      = document.getElementById('email');
  const passwordInput   = document.getElementById('password');
  const emailField      = document.getElementById('emailField');
  const passwordField   = document.getElementById('passwordField');
  const emailError      = document.getElementById('emailError');
  const passwordError   = document.getElementById('passwordError');
  const formStatus      = document.getElementById('formStatus');
  const loginBtn        = document.getElementById('loginBtn');
  const googleBtn       = document.getElementById('googleBtn');
  const passwordToggle  = document.getElementById('passwordToggle');
  const forgotLink      = document.getElementById('forgotPasswordLink');

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

  /* Google error params ----------------------------------- */
  const params = new URLSearchParams(window.location.search);
  if (params.get('google_error') === 'not_configured') showStatus('Google sign-in is not set up on this server.', 'error');
  if (params.get('google_error') === 'auth_failed')     showStatus('Google sign-in failed. Please try again.', 'error');

  /* Password toggle --------------------------------------- */
  passwordToggle.addEventListener('click', () => {
    const show = passwordInput.type === 'password';
    passwordInput.type = show ? 'text' : 'password';
    passwordToggle.classList.toggle('is-visible', show);
    passwordToggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });

  /* Validation -------------------------------------------- */
  function isValidEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()); }

  function setErr(field, errEl, msg) { field.classList.add('has-error'); errEl.textContent = msg; }
  function clrErr(field, errEl)      { field.classList.remove('has-error'); errEl.textContent = ''; }

  function validateEmail()    {
    if (!emailInput.value.trim())         { setErr(emailField, emailError, 'Email is required.'); return false; }
    if (!isValidEmail(emailInput.value))  { setErr(emailField, emailError, 'Enter a valid email address.'); return false; }
    clrErr(emailField, emailError); return true;
  }
  function validatePassword() {
    if (!passwordInput.value) { setErr(passwordField, passwordError, 'Password is required.'); return false; }
    clrErr(passwordField, passwordError); return true;
  }

  emailInput.addEventListener('input',    () => { if (emailField.classList.contains('has-error'))    validateEmail(); });
  passwordInput.addEventListener('input', () => { if (passwordField.classList.contains('has-error')) validatePassword(); });

  /* Status ------------------------------------------------ */
  function showStatus(msg, type) {
    formStatus.textContent = msg;
    formStatus.className = 'form-status ' + (type === 'success' ? 'is-success' : 'is-error');
  }

  /* Ripple ------------------------------------------------ */
  function ripple(btn, e) {
    const r = btn.getBoundingClientRect();
    btn.style.setProperty('--ripple-x', (e.clientX - r.left) + 'px');
    btn.style.setProperty('--ripple-y', (e.clientY - r.top)  + 'px');
    btn.classList.remove('is-rippling');
    void btn.offsetWidth;
    btn.classList.add('is-rippling');
  }
  loginBtn.addEventListener('click',  e => ripple(loginBtn, e));
  googleBtn.addEventListener('click', e => ripple(googleBtn, e));

  /* Login submit ------------------------------------------ */
  loginForm.addEventListener('submit', async e => {
    e.preventDefault();
    formStatus.className = 'form-status';
    formStatus.textContent = '';

    if (!validateEmail() | !validatePassword()) return;

    loginBtn.classList.add('is-loading');
    loginBtn.disabled = true;

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({
          email: emailInput.value.trim(),
          password: passwordInput.value,
          remember: document.getElementById('rememberMe').checked
        })
      });
      const data = await res.json();
      if (res.ok) {
        showStatus(data.message || 'Login successful. Redirecting…', 'success');
        setTimeout(() => { window.location.href = data.redirect || '/dashboard'; }, 800);
      } else {
        showStatus(data.message || 'Invalid email or password.', 'error');
        loginBtn.classList.remove('is-loading');
        loginBtn.disabled = false;
      }
    } catch (err) {
      showStatus('Connection error. Please try again.', 'error');
      loginBtn.classList.remove('is-loading');
      loginBtn.disabled = false;
    }
  });

  /* Google ------------------------------------------------ */
  googleBtn.addEventListener('click', () => { window.location.href = '/api/auth/google/login'; });

  /* Forgot password --------------------------------------- */
  forgotLink.addEventListener('click', async e => {
    e.preventDefault();
    formStatus.className = 'form-status';
    formStatus.textContent = '';

    if (!validateEmail()) {
      emailInput.focus();
      showStatus('Enter your email above first, then click Forgot password.', 'error');
      return;
    }

    try {
      const res = await fetch('/api/forgot-password', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ email: emailInput.value.trim() })
      });
      const data = await res.json();
      showStatus(data.message, res.ok ? 'success' : 'error');
    } catch (err) {
      showStatus('Could not reach the server. Please try again.', 'error');
    }
  });
});
