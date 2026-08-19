function formatLocalDates(){
  document.querySelectorAll('td').forEach(cell=>{
    const value=cell.textContent.trim();
    if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)) return;
    const date=new Date(value);
    if(Number.isNaN(date.getTime())) return;
    cell.textContent=date.toLocaleString('ru-RU',{
      day:'2-digit',month:'2-digit',year:'numeric',
      hour:'2-digit',minute:'2-digit'
    });
  });
}

new MutationObserver(formatLocalDates).observe(document.body,{childList:true,subtree:true});
formatLocalDates();
