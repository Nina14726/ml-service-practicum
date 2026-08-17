function isAuthenticated(){return Boolean(localStorage.getItem('ml_token'))}

function updateAuthUI(){
  const loggedIn=isAuthenticated();
  document.getElementById('accountNav')?.classList.toggle('hidden',loggedIn);
  document.getElementById('cabinetNav')?.classList.toggle('hidden',!loggedIn);
  document.getElementById('historyNav')?.classList.toggle('hidden',!loggedIn);
  document.getElementById('logoutNav')?.classList.toggle('hidden',!loggedIn);
}

const originalShow=window.show;
window.show=function(id){
  if((id==='cabinet'||id==='history')&&!isAuthenticated()){
    originalShow('account');
    return;
  }
  originalShow(id);
};

const originalLoginUser=window.loginUser;
window.loginUser=async function(e){
  await originalLoginUser(e);
  updateAuthUI();
};

window.logout=function(){
  localStorage.removeItem('ml_token');
  updateAuthUI();
  originalShow('account');
};

updateAuthUI();
