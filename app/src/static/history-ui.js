function formatHistoryDate(value){
  const date=new Date(value);
  if(Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('ru-RU',{
    day:'2-digit',
    month:'2-digit',
    year:'numeric',
    hour:'2-digit',
    minute:'2-digit'
  });
}

async function loadTasks(){
  try{
    const d=await req('/web/api/tasks');
    const items=d.filter(x=>x.model==='video_analysis');
    tasksBody.innerHTML=items.length?items.map(x=>`<tr><td>${formatHistoryDate(x.created_at)}</td><td>${x.source_name??'Видео'}</td><td>${x.status}</td><td>${x.charged_credits}</td><td>${x.worker_id??''}</td><td class="history-actions">${x.result?`<button onclick="openTask('${x.task_id}')">Открыть</button>`:(x.error??'')}</td></tr>`).join(''):`<tr><td colspan="6">Анализов пока нет</td></tr>`;
  }catch(x){
    tasksBody.innerHTML=`<tr><td colspan="6">${x.message}</td></tr>`;
  }
}

async function loadTransactions(){
  try{
    const d=await req('/history/transactions');
    txBody.innerHTML=d.map(x=>`<tr><td>${formatHistoryDate(x.created_at)}</td><td>${x.transaction_type}</td><td>${x.amount}</td><td>${x.request_id??''}</td></tr>`).join('');
  }catch(x){
    txBody.innerHTML=`<tr><td colspan="4">${x.message}</td></tr>`;
  }
}
