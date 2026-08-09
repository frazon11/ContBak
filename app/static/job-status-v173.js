// ContBak 1.7.3: warning is a terminal backup state, not success and not running.
function renderJob(container,button,job){
  const box=ensureProgress(container);if(!box)return;
  const progress=Number(job.progress||0);box.classList.add('active');
  box.querySelector('.progress-percent').textContent=`${progress}%`;
  box.querySelector('.progress-bar').style.width=`${progress}%`;
  box.querySelector('.progress-message').textContent=job.message||t('backup_running_dots');
  box.querySelector('.progress-log-lines').innerHTML=(job.log||[]).map(line=>`<div><time>${line.time}</time><span>${escapeHtml(line.message)}</span></div>`).join('');
  box.classList.toggle('success',job.status==='success');
  box.classList.toggle('warning',job.status==='warning');
  box.classList.toggle('error',job.status==='error');
  if(['success','warning','error'].includes(job.status)){
    button.disabled=false;
    button.textContent=job.status==='error'?t('try_again'):t('back_up_now');
  }
}

async function pollJob(jobId,container,button){
  try{
    const response=await fetch(`/api/jobs/${jobId}`,{headers:{Accept:'application/json'}});const job=await response.json();
    if(!response.ok)throw new Error(job.detail||job.error||t('job_status_failed'));
    renderJob(container,button,job);
    if(job.status==='success'){
      showToast(`${job.container_name}: ${job.message||t('backup_completed')}`,'success');
      setTimeout(()=>location.reload(),1500);return;
    }
    if(job.status==='warning'){
      showToast(`${job.container_name}: ${job.message||'Backup completed with warnings.'}`,'warning');
      setTimeout(()=>location.reload(),2500);return;
    }
    if(job.status==='error'){
      showToast(`${job.container_name}: ${job.error||job.message}`,'error');return;
    }
    setTimeout(()=>pollJob(jobId,container,button),1000);
  }catch(error){button.disabled=false;button.textContent=t('try_again');showToast(error.message,'error')}
}
