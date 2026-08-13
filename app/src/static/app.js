let currentResult=null;
function show(id){document.querySelectorAll('main>section').forEach(x=>x.classList.add('hidden'));document.getElementById(id).classList.remove('hidden');if(id==='cabinet')loadBalance();if(id==='history'){loadTasks();loadTransactions()}}
function box(id,msg,ok=true){document.getElementById(id).innerHTML=`<div class="status ${ok?'ok':'err'}">${msg}</div>`}
