/* =========================================================
   VERIDICT — RESET PASSWORD PAGE LOGIC
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {

  const resetTokenInput = document.getElementById('resetToken');
  const newPasswordInput = document.getElementById('newPassword');
  const confirmPasswordInput = document.getElementById('confirmPassword');
  const newPasswordField = document.getElementById('newPasswordField');
  const confirmPasswordField = document.getElementById('confirmPasswordField');
  const newPasswordError = document.getElementById('newPasswordError');
  const confirmPasswordError = document.getElementById('confirmPasswordError');
  const resetBtn = document.getElementById('resetBtn');
  const resetStatus = document.getElementById('resetStatus');
  const backArrow = document.getElementById('backArrow');
  const invalidTokenState = document.getElementById('invalidTokenState');
  const resetFormState = document.getElementById('resetFormState');

  let csrfToken = '';

  /* ---------------------------------------------------------
     BACK ARROW
     --------------------------------------------------------- */
  backArrow.addEventListener('click', () => {
    window.location.href = '/login';
  });

  /* ---------------------------------------------------------
     READ TOKEN FROM URL
     --------------------------------------------------------- */
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');

  if (!token) {
    resetFormState.hidden = true;
    invalidTokenState.hidden = false;
  } else {
    resetTokenInput.value = token;
  }

  /* ---------------------------------------------------------
     CSRF TOKEN
     --------------------------------------------------------- */
  async function init() {
    try {
      const res = await fetch('/api/csrf-token', { credentials: 'same-origin' });
      const data = await res.json();
      csrfToken = data.csrf_token || '';
    } catch (err) {
      console.error('CSRF token fetch failed:', err);
    }
  }
  init();

  /* ---------------------------------------------------------
     PASSWORD TOGGLES
     --------------------------------------------------------- */
  function wireToggle(toggleId, inputEl) {
    document.getElementById(toggleId).addEventListener('click', () => {
      const isVisible = inputEl.type === 'text';
      inputEl.type = isVisible ? 'password' : 'text';
      document.getElementById(toggleId).classList.toggle('is-visible', !isVisible);
      document.getElementById(toggleId).setAttribute('aria-label', isVisible ? 'Show password' : 'Hide password');
    });
  }
  wireToggle('newPasswordToggle', newPasswordInput);
  wireToggle('confirmPasswordToggle', confirmPasswordInput);

  /* ---------------------------------------------------------
     VALIDATION
     --------------------------------------------------------- */
  function setFieldError(field, errorEl, msg) {
    field.classList.add('has-error');
    errorEl.textContent = msg;
  }

  function clearFieldError(field, errorEl) {
    field.classList.remove('has-error');
    errorEl.textContent = '';
  }

  function showStatus(msg, type) {
    resetStatus.textContent = msg;
    resetStatus.classList.remove('is-error', 'is-success');
    resetStatus.classList.add(type === 'success' ? 'is-success' : 'is-error');
  }

  /* ---------------------------------------------------------
     SUBMIT
     --------------------------------------------------------- */
  document.getElementById('resetForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    let valid = true;
    clearFieldError(newPasswordField, newPasswordError);
    clearFieldError(confirmPasswordField, confirmPasswordError);

    if (newPasswordInput.value.length < 8) {
      setFieldError(newPasswordField, newPasswordError, 'Password must be at least 8 characters.');
      valid = false;
    }

    if (confirmPasswordInput.value !== newPasswordInput.value) {
      setFieldError(confirmPasswordField, confirmPasswordError, 'Passwords do not match.');
      valid = false;
    }

    if (!valid) return;

    resetBtn.classList.add('is-loading');
    resetBtn.disabled = true;

    try {
      const res = await fetch('/api/reset-password', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          token: resetTokenInput.value,
          new_password: newPasswordInput.value
        })
      });

      const data = await res.json();

      if (res.ok) {
        showStatus('Password reset! Redirecting to your dashboard…', 'success');
        setTimeout(() => { window.location.href = data.redirect || '/dashboard'; }, 1200);
      } else if (res.status === 400 && data.message.includes('expired')) {
        resetFormState.hidden = true;
        invalidTokenState.hidden = false;
      } else {
        showStatus(data.message || 'Could not reset password. Please try again.', 'error');
        resetBtn.classList.remove('is-loading');
        resetBtn.disabled = false;
      }
    } catch (err) {
      showStatus('Something went wrong. Check your connection and try again.', 'error');
      resetBtn.classList.remove('is-loading');
      resetBtn.disabled = false;
    }
  });
});
