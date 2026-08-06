from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/web", response_class=HTMLResponse)
def web_app() -> str:
    return r'''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ML Service — личный кабинет</title>
  <style>
    :root{font-family:Inter,system-ui,sans-serif;color:#172033;background:#f5f7fb}
    *{box-sizing:border-box} body{margin:0}.wrap{max-width:1100px;margin:auto;padding:24px}
    header{background:#172033;color:white}.hero{padding:44px 24px}.hero h1{margin:0 0 10px;font-size:38px}
    nav{display:flex;gap:12px;flex-wrap:wrap;margin-top:20px}button,.button{border:0;border-radius:10px;padding:11px 16px;background:#5b5bd6;color:white;cursor:pointer;font-weight:600}
    button.secondary{background:#e7e9f4;color:#172033}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:18px;margin-top:22px}
    .card{background:white;border-radius:16px;padding:20px;box-shadow:0 8px 30px #17203312}.card h2{margin-top:0}
    input,select,textarea{width:100%;padding:11px;border:1px solid #ccd1df;border-radius:9px;margin:6px 0 12px;font:inherit}
    textarea{min-height:110px}.muted{color:#697386}.status{padding:12px;border-radius:9px;margin-top:12px;white-space:pre-wrap}.ok{background:#e8f7ee;color:#17663a}.err{background:#fdecec;color:#922}
    table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #edf0f5;vertical-align:top}
    .hidden{display:none}.balance{font-size:34px;font-weight:800}.wide{grid-column:1/-1}
  </style>
</head>
<body>
<header><div class="wrap hero"><h1>ML Service</h1><p>Личный кабинет для отправки ML-задач, управления балансом и просмотра истории.</p><nav><button onclick="show('home')">Главная</button><button onclick="show('account')">Аккаунт</button><button onclick="show('cabinet')">Личный кабинет</button><button onclick="logout()" class="secondary">Выйти</button></nav></div></header>
<main class="wrap">
<section id="home"><div class="grid"><article class="card"><h2>Что умеет сервис</h2><p>Принимает признаки через REST API, проверяет баланс, ставит задачу в RabbitMQ и обрабатывает её несколькими ML-воркерами.</p></article><article class="card"><h2>Сквозной сценарий</h2><p>Регистрация → пополнение баланса → отправка данных → получение результата → история операций.</p></article></div></section>
<section id="account" class="hidden"><div class="grid"><form class="card" onsubmit="registerUser(event)"><h2>Регистрация</h2><input id="regEmail" type="email" placeholder="Email" required><input id="regPassword" type="password" placeholder="Пароль" minlength="4" required><button>Создать аккаунт</button><div id="regStatus"></div></form><form class="card" onsubmit="loginUser(event)"><h2>Авторизация</h2><input id="loginEmail" type="email" placeholder="Email" required><input id="loginPassword" type="password" placeholder="Пароль" required><button>Войти</button><div id="loginStatus"></div></form></div></section>
<section id="cabinet" class="hidden"><div class="grid"><article class="card"><h2>Баланс</h2><div id="balance" class="balance">—</div><button onclick="loadBalance()">Обновить</button></article><form class="card" onsubmit="topUp(event)"><h2>Пополнение</h2><input id="topupAmount" type="number" min="0.01" step="0.01" value="10" required><button>Пополнить</button><div id="topupStatus"></div></form><form class="card wide" onsubmit="sendPrediction(event)"><h2>ML-запрос</h2><label>Модель</label><select id="model"><option value="demo_model">demo_model</option></select><label>Признаки в JSON</label><textarea id="features">{"x1": 1.2, "x2": 5.7}</textarea><button>Отправить</button><div id="predictStatus"></div></form><article class="card wide"><h2>История задач</h2><button onclick="loadTasks()">Обновить</button><div style="overflow:auto"><table><thead><tr><th>Дата</th><th>Задача</th><th>Статус</th><th>Предсказание</th><th>Списано</th><th>Воркер</th><th>Ошибка</th></tr></thead><tbody id="tasksBody"></tbody></table></div></article><article class="card wide"><h2>История транзакций</h2><button onclick="loadTransactions()">Обновить</button><div style="overflow:auto"><table><thead><tr><th>Дата</th><th>Тип</th><th>Сумма</th><th>Request ID</th></tr></thead><tbody id="txBody"></tbody></table></div></article></div></section>
</main>
<script>
const api=''; const token=()=>localStorage.getItem('ml_token');
function show(id){document.querySelectorAll('main>section').forEach(x=>x.classList.add('hidden'));document.getElementById(id).classList.remove('hidden');if(id==='cabinet'){loadBalance();loadTasks();loadTransactions()}}
function box(id,msg,ok=true){document.getElementById(id).innerHTML=`<div class="status ${ok?'ok':'err'}">${msg}</div>`}
async function req(path,opt={}){opt.headers={...(opt.headers||{}),'Content-Type':'application/json'};if(token())opt.headers.Authorization='Bearer '+token();const r=await fetch(api+path,opt);let data;try{data=await r.json()}catch{data={detail:await r.text()}}const msg=Array.isArray(data.detail)?data.detail.map(e=>`${(e.loc||[]).slice(1).join('.')}: ${e.msg}`).join('; '):(data.detail||JSON.stringify(data));if(!r.ok)throw new Error(msg);return data}
async function registerUser(e){e.preventDefault();try{const d=await req('/auth/register',{method:'POST',body:JSON.stringify({email:regEmail.value,password:regPassword.value})});box('regStatus','Пользователь создан: '+d.email)}catch(x){box('regStatus',x.message,false)}}
async function loginUser(e){e.preventDefault();try{const d=await req('/auth/login',{method:'POST',body:JSON.stringify({email:loginEmail.value,password:loginPassword.value})});localStorage.setItem('ml_token',d.access_token);box('loginStatus','Авторизация успешна');show('cabinet')}catch(x){box('loginStatus',x.message,false)}}
function logout(){localStorage.removeItem('ml_token');show('account')}
async function loadBalance(){try{const d=await req('/balance');document.getElementById('balance').textContent=d.amount+' кредитов'}catch(x){document.getElementById('balance').textContent='Нужна авторизация'}}
async function topUp(e){e.preventDefault();try{const d=await req('/balance/top-up',{method:'POST',body:JSON.stringify({amount:Number(topupAmount.value)})});box('topupStatus','Новый баланс: '+d.amount);loadBalance();loadTransactions()}catch(x){box('topupStatus',x.message,false)}}
async function sendPrediction(e){e.preventDefault();let f;try{f=JSON.parse(features.value)}catch{box('predictStatus','Некорректный JSON',false);return}try{const d=await req('/predict',{method:'POST',body:JSON.stringify({features:f,model:model.value})});box('predictStatus','Задача поставлена: '+d.task_id);poll(d.task_id)}catch(x){box('predictStatus',x.message,false)}}
async function poll(id){for(let i=0;i<20;i++){await new Promise(r=>setTimeout(r,700));try{const d=await req('/predict/'+id);if(d.status!=='queued'){box('predictStatus',JSON.stringify(d,null,2),d.status==='success');loadBalance();loadTasks();loadTransactions();return}}catch{}}box('predictStatus','Задача ещё обрабатывается',false)}
async function loadTasks(){try{const d=await req('/web/api/tasks');tasksBody.innerHTML=d.map(x=>`<tr><td>${x.created_at}</td><td>${x.task_id}</td><td>${x.status}</td><td>${x.prediction??''}</td><td>${x.charged_credits}</td><td>${x.worker_id??''}</td><td>${x.error??''}</td></tr>`).join('')}catch(x){tasksBody.innerHTML=`<tr><td colspan="7">${x.message}</td></tr>`}}
async function loadTransactions(){try{const d=await req('/history/transactions');txBody.innerHTML=d.map(x=>`<tr><td>${x.created_at}</td><td>${x.transaction_type}</td><td>${x.amount}</td><td>${x.request_id??''}</td></tr>`).join('')}catch(x){txBody.innerHTML=`<tr><td colspan="4">${x.message}</td></tr>`}}
</script></body></html>'''
