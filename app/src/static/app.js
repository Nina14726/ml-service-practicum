const api='';
const token=()=>localStorage.getItem('ml_token');
let currentResult=null;
function show(id){document.querySelectorAll('main>section').forEach(x=>x.classList.add('hidden'));document.getElementById(id).classList.remove('hidden');if(id==='cabinet')loadBalance();if(id==='history'){loadTasks();loadTransactions()}}
function box(id,msg,ok=true){document.getElementById(id).innerHTML=`<div class="status ${ok?'ok':'err'}">${msg}</div>`}
async function req(path,opt={}){opt.headers={...(opt.headers||{}),'Content-Type':'application/json'};if(token())opt.headers.Authorization='Bearer '+token();const r=await fetch(api+path,opt);let data;try{data=await r.json()}catch{data={detail:await r.text()}}const msg=Array.isArray(data.detail)?data.detail.map(e=>`${(e.loc||[]).slice(1).join('.')}: ${e.msg}`).join('; '):(data.detail||JSON.stringify(data));if(!r.ok)throw new Error(msg);return data}
async function registerUser(e){e.preventDefault();try{const d=await req('/auth/register',{method:'POST',body:JSON.stringify({email:regEmail.value,password:regPassword.value})});box('regStatus','Пользователь создан: '+d.email)}catch(x){box('regStatus',x.message,false)}}
async function loginUser(e){e.preventDefault();try{const d=await req('/auth/login',{method:'POST',body:JSON.stringify({email:loginEmail.value,password:loginPassword.value})});localStorage.setItem('ml_token',d.access_token);box('loginStatus','Авторизация успешна');show('cabinet')}catch(x){box('loginStatus',x.message,false)}}
function logout(){localStorage.removeItem('ml_token');show('account')}
async function loadBalance(){try{const d=await req('/balance');document.getElementById('balance').textContent=d.amount+' кредитов'}catch{document.getElementById('balance').textContent='Нужна авторизация'}}
async function topUp(e){e.preventDefault();try{const d=await req('/balance/top-up',{method:'POST',body:JSON.stringify({amount:Number(topupAmount.value)})});box('topupStatus','Новый баланс: '+d.amount);loadBalance();loadTransactions()}catch(x){box('topupStatus',x.message,false)}}
