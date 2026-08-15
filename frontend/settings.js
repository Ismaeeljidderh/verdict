document.addEventListener('DOMContentLoaded', async () => {
  let csrfToken='', currentUser=null;
  try{const r=await fetch('/api/csrf-token',{credentials:'same-origin'});csrfToken=(await r.json()).csrf_token||'';}catch(e){}
  try{
    const r=await fetch('/api/me',{credentials:'same-origin'});
    if(r.status===401){window.location.href='/login';return;}
    currentUser=await r.json(); populateUser(currentUser);
  }catch(e){ console.error('Could not load user',e); }

  function populateUser(me) {
    const initial=(me.full_name||me.username||'V').charAt(0).toUpperCase();
    const displayName=me.full_name||me.username||'User';
    document.getElementById('topbarAvatar').textContent=initial;
    document.getElementById('topbarName').textContent=displayName;
    document.getElementById('settingsAvatar').textContent=initial;
    document.getElementById('settingsDisplayName').textContent=displayName;
    document.getElementById('settingsDisplayEmail').textContent=me.email||'';
    document.getElementById('settingsDisplayUsername').textContent='@'+(me.username||'');
    const planBadge=document.getElementById('settingsPlanBadge');
    if(me.is_premium){planBadge.textContent='✓ Premium';planBadge.style.background='var(--v-grad)';planBadge.style.color='#fff';}
    else{planBadge.textContent='Free Plan';}
    if(!me.has_password && me.has_google){
      document.getElementById('passwordSectionSub').textContent='This account signs in with Google. Password change is not available.';
      document.getElementById('passwordForm').querySelectorAll('input,button').forEach(el=>{el.disabled=true;el.style.opacity='0.4';});
    }
    document.getElementById('settingsFullName').value=me.full_name||'';
    document.getElementById('settingsUsername').value=me.username||'';
    document.getElementById('settingsEmail').value=me.email||'';
  }

  function showStatus(id,msg,type){const el=document.getElementById(id);el.textContent=msg;el.className='form-status '+(type==='success'?'is-success':'is-error');}
  function setLoading(id,on){const b=document.getElementById(id);b.classList.toggle('is-loading',on);b.disabled=on;}

  document.getElementById('profileForm').addEventListener('submit', async e => {
    e.preventDefault();
    const fullName=document.getElementById('settingsFullName').value.trim(), username=document.getElementById('settingsUsername').value.trim();
    if(!fullName){showStatus('profileStatus','Full name is required.','error');return;}
    if(!/^[a-zA-Z0-9_]{3,20}$/.test(username)){showStatus('profileStatus','Username: 3-20 chars, letters/numbers/underscores.','error');return;}
    setLoading('profileSaveBtn',true);
    try{
      const r=await fetch('/api/me',{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({full_name:fullName,username})});
      const d=await r.json();
      if(r.ok){showStatus('profileStatus','✓ Profile updated.','success');currentUser={...currentUser,full_name:fullName,username};populateUser(currentUser);}
      else{showStatus('profileStatus',d.message||'Could not update profile.','error');}
    }catch(e){showStatus('profileStatus','Connection error.','error');}
    finally{setLoading('profileSaveBtn',false);}
  });

  document.getElementById('passwordForm').addEventListener('submit', async e => {
    e.preventDefault();
    const current=document.getElementById('currentPassword').value, newPw=document.getElementById('newPassword').value, confirm=document.getElementById('confirmNewPassword').value;
    if(!current){showStatus('passwordStatus','Enter your current password.','error');return;}
    if(newPw.length<8){showStatus('passwordStatus','New password must be at least 8 characters.','error');return;}
    if(confirm!==newPw){showStatus('passwordStatus','Passwords do not match.','error');return;}
    setLoading('passwordSaveBtn',true);
    try{
      const r=await fetch('/api/change-password',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({current_password:current,new_password:newPw})});
      const d=await r.json();
      if(r.ok){showStatus('passwordStatus','✓ Password updated.','success');document.getElementById('passwordForm').reset();}
      else{showStatus('passwordStatus',d.message||'Could not update password.','error');}
    }catch(e){showStatus('passwordStatus','Connection error.','error');}
    finally{setLoading('passwordSaveBtn',false);}
  });

  document.getElementById('deleteForm').addEventListener('submit', async e => {
    e.preventDefault();
    const confirm=document.getElementById('deleteConfirm').value.trim().toUpperCase();
    if(confirm!=='DELETE'){showStatus('deleteStatus','Type DELETE exactly to confirm.','error');return;}
    setLoading('deleteBtn',true);
    try{
      const r=await fetch('/api/me',{method:'DELETE',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrfToken},body:JSON.stringify({confirm:'DELETE'})});
      const d=await r.json();
      if(r.ok){showStatus('deleteStatus','Account deleted. Redirecting…','success');setTimeout(()=>{window.location.href=d.redirect||'/';},1200);}
      else{showStatus('deleteStatus',d.message||'Could not delete account.','error');setLoading('deleteBtn',false);}
    }catch(e){showStatus('deleteStatus','Connection error.','error');setLoading('deleteBtn',false);}
  });
});