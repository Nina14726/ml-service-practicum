function isAuthenticated(){return Boolean(localStorage.getItem('ml_token'))}

function updateAuthUI(loggedIn=isAuthenticated()){
  document.getElementById('accountNav')?.classList.toggle('hidden',loggedIn);
  document.getElementById('cabinetNav')?.classList.toggle('hidden',!loggedIn);
  document.getElementById('historyNav')?.classList.toggle('hidden',!loggedIn);
  document.getElementById('logoutNav')?.classList.toggle('hidden',!loggedIn);
}

async function validateSession(){
  const savedToken=localStorage.getItem('ml_token');
  if(!savedToken){
    updateAuthUI(false);
    return false;
  }
  try{
    const response=await fetch('/balance',{headers:{Authorization:'Bearer '+savedToken}});
    if(!response.ok)throw new Error('invalid session');
    updateAuthUI(true);
    return true;
  }catch{
    localStorage.removeItem('ml_token');
    updateAuthUI(false);
    return false;
  }
}

const originalShow=window.show;
window.show=async function(id){
  if(id==='cabinet'||id==='history'){
    const loggedIn=await validateSession();
    if(!loggedIn){
      originalShow('account');
      return;
    }
  }
  originalShow(id);
};

const originalLoginUser=window.loginUser;
window.loginUser=async function(e){
  await originalLoginUser(e);
  await validateSession();
};

window.logout=function(){
  localStorage.removeItem('ml_token');
  updateAuthUI(false);
  originalShow('account');
};

validateSession();
