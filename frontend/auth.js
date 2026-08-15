(function () {
  'use strict';
  let csrfToken = '';
  async function loadCsrf() { try { const r=await fetch('/api/csrf-token',{credentials:'same-origin'}); csrfToken=(await r.json()).csrf_token||''; } catch(e){} }
  function isValidEmail(v){return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());}
  function isValidUsername(v){return /^[a-zA-Z0-9_]{3,20}$/.test(v.trim());}
  function setErr(w,e,m){document.getElementById(w)?.classList.add('has-error');const el=document.getElementById(e);if(el)el.textContent=m;}
  function clrErr(w,e){document.getElementById(w)?.classList.remove('has-error');const el=document.getElementById(e);if(el)el.textContent='';}
  function showStatus(id,msg,type){const el=document.getElementById(id);if(!el)return;el.textContent=msg;el.className='form-status '+(type==='success'?'is-success':'is-error');}
  function setLoading(id,on){const b=document.getElementById(id);if(!b)return;b.classList.toggle('is-loading',on);b.disabled=on;}
  function wirePwToggle(tid,iid){const t=document.getElementById(tid),i=document.getElementById(iid);if(!t||!i)return;t.addEventListener('click',()=>{const show=i.type==='password';i.type=show?'text':'password';t.classList.toggle('is-visible',show);});}

  function initLogin() {
    const form=document.getElementById('loginForm'); if(!form)return;
    const emailIn=document.getElementById('email'), passIn=document.getElementById('password');
    wirePwToggle('passwordToggle','password');
    const params=new URLSearchParams(window.location.search);
    if(params.get('google_error')==='not_configured') showStatus('formStatus','Google sign-in is not set up on this server.','error');
    if(params.get('google_error')==='auth_failed') showStatus('formStatus','Google sign-in failed. Please try again.','error');
    function validateEmail(){if(!emailIn.value.trim()){setErr('emailField','emailError','Email is required.');return false;}if(!isValidEmail(emailIn.value)){setErr('emailField','emailError','Enter a valid email address.');return false;}clrErr('emailField','emailError');return true;}
    function validatePass(){if(!passIn.value){setErr('passwordField','passwordError','Password is required.');return false;}clrErr('passwordField','passwordError');return true;}
    emailIn.addEventListener('input',()=>{if(document.getElementById('emailField')?.classList.contains('has-error'))validateEmail();});
    passIn.addEventListener('input',()=>{if(document.getElementById('passwordField')?.classList.contains('has-error'))validatePass();});
    form.addEventListener('submit', async e => {
      e.preventDefault(); showStatus('formStatus','','');
      const okE=validateEmail(), okP=validatePass(); if(!okE||!okP)return;
      setLoading('loginBtn',true);
      try {
        const res=await fetch('/api/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({email:emailIn.value.trim(),password:passIn.value,remember:document.getElementById('rememberMe')?.checked})});
        const d=await res.json();
        if(res.ok){showStatus('formStatus',d.message||'Redirecting…','success');setTimeout(()=>{window.location.href=d.redirect||'/dashboard';},800);}
        else{showStatus('formStatus',d.message||'Invalid email or password.','error');setLoading('loginBtn',false);}
      } catch { showStatus('formStatus','Connection error. Please try again.','error'); setLoading('loginBtn',false); }
    });
    document.getElementById('googleBtn')?.addEventListener('click', () => { window.location.href='/api/auth/google/login'; });
    document.getElementById('forgotPasswordLink')?.addEventListener('click', async e => {
      e.preventDefault(); showStatus('formStatus','','');
      if(!validateEmail()){emailIn.focus();showStatus('formStatus','Enter your email above first, then click Forgot password.','error');return;}
      try{
        const res=await fetch('/api/forgot-password',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({email:emailIn.value.trim()})});
        const d=await res.json(); showStatus('formStatus',d.message,res.ok?'success':'error');
      } catch { showStatus('formStatus','Connection error.','error'); }
    });
  }

  function initRegister() {
    const form=document.getElementById('registerForm'); if(!form)return;
    wirePwToggle('regPasswordToggle','regPassword'); wirePwToggle('confirmPasswordToggle','confirmPassword');
    function showStatus2(msg,type){const el=document.getElementById('registerFormStatus');if(!el)return;el.textContent=msg;el.className='form-status '+(type==='success'?'is-success':'is-error');}
    function validate(){
      let ok=true;
      const fn=document.getElementById('fullName')?.value.trim(), un=document.getElementById('username')?.value.trim(), em=document.getElementById('regEmail')?.value.trim(), pw=document.getElementById('regPassword')?.value, cf=document.getElementById('confirmPassword')?.value;
      if(!fn){setErr('fullNameField','fullNameError','Full name is required.');ok=false;}else clrErr('fullNameField','fullNameError');
      if(!isValidUsername(un)){setErr('usernameField','usernameError','3-20 chars: letters, numbers, underscores.');ok=false;}else clrErr('usernameField','usernameError');
      if(!isValidEmail(em)){setErr('regEmailField','regEmailError','Enter a valid email address.');ok=false;}else clrErr('regEmailField','regEmailError');
      if((pw||'').length<8){setErr('regPasswordField','regPasswordError','At least 8 characters.');ok=false;}else clrErr('regPasswordField','regPasswordError');
      if(cf!==pw||!cf){setErr('confirmPasswordField','confirmPasswordError','Passwords do not match.');ok=false;}else clrErr('confirmPasswordField','confirmPasswordError');
      if(!document.getElementById('agreeTerms')?.checked){showStatus2('You must agree to the Terms and Privacy Policy.','error');ok=false;}
      return ok;
    }
    form.addEventListener('submit', async e => {
      e.preventDefault(); const s=document.getElementById('registerFormStatus'); if(s){s.textContent='';s.className='form-status';}
      if(!validate())return; setLoading('registerBtn',true);
      try{
        const res=await fetch('/api/register',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({full_name:document.getElementById('fullName').value.trim(),username:document.getElementById('username').value.trim(),email:document.getElementById('regEmail').value.trim().toLowerCase(),password:document.getElementById('regPassword').value})});
        const d=await res.json();
        if(res.ok){showStatus2(d.message||'Account created! Redirecting…','success');setTimeout(()=>{window.location.href=d.redirect||'/dashboard';},900);}
        else{showStatus2(d.message||'Could not create account.','error');setLoading('registerBtn',false);}
      } catch { showStatus2('Connection error. Please try again.','error'); setLoading('registerBtn',false); }
    });
  }

  function initResetPassword() {
    const form=document.getElementById('resetForm'); if(!form)return;
    const params=new URLSearchParams(window.location.search); const token=params.get('token');
    if(!token){document.getElementById('resetFormState').hidden=true;document.getElementById('invalidTokenState').hidden=false;return;}
    document.getElementById('resetToken').value=token;
    wirePwToggle('newPasswordToggle','newPassword'); wirePwToggle('confirmPasswordToggle','confirmPassword');
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const newPw=document.getElementById('newPassword').value, cfPw=document.getElementById('confirmPassword').value;
      let ok=true;
      if(newPw.length<8){setErr('newPasswordField','newPasswordError','At least 8 characters.');ok=false;}else clrErr('newPasswordField','newPasswordError');
      if(cfPw!==newPw){setErr('confirmPasswordField','confirmPasswordError','Passwords do not match.');ok=false;}else clrErr('confirmPasswordField','confirmPasswordError');
      if(!ok)return; setLoading('resetBtn',true);
      try{
        const res=await fetch('/api/reset-password',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({token,new_password:newPw})});
        const d=await res.json();
        if(res.ok){const el=document.getElementById('resetStatus');if(el){el.textContent='Password reset! Redirecting…';el.className='form-status is-success';}setTimeout(()=>{window.location.href=d.redirect||'/dashboard';},1200);}
        else{if(res.status===400&&d.message?.includes('expired')){document.getElementById('resetFormState').hidden=true;document.getElementById('invalidTokenState').hidden=false;}else{const el=document.getElementById('resetStatus');if(el){el.textContent=d.message||'Could not reset password.';el.className='form-status is-error';}setLoading('resetBtn',false);}}
      } catch { const el=document.getElementById('resetStatus'); if(el){el.textContent='Connection error.';el.className='form-status is-error';} setLoading('resetBtn',false); }
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    await loadCsrf();
    if(document.getElementById('loginForm')) initLogin();
    else if(document.getElementById('registerForm')) initRegister();
    else if(document.getElementById('resetForm')) initResetPassword();
  });
})();