const content=document.querySelector("#content");
const notice=document.querySelector("#notice");
const modal=document.querySelector("#progress-modal");
const progressBar=document.querySelector("#progress-bar");
const progressPercent=document.querySelector("#progress-percent");
const progressStage=document.querySelector("#progress-stage");
const progressMessage=document.querySelector("#progress-message");
const progressTitle=document.querySelector("#progress-title");
const progressClose=document.querySelector("#progress-close");
let currentView="dashboard";
let activeJob=null;

function showMessage(text,error=false){notice.textContent=text;notice.classList.toggle("error",error);notice.classList.remove("hidden")}
function clearMessage(){notice.classList.add("hidden")}
async function api(url,options={}){const response=await fetch(url,{headers:{"Content-Type":"application/json"},...options});const body=await response.json().catch(()=>({}));if(!response.ok)throw new Error(body.detail||`HTTP ${response.status}`);return body}
function size(bytes){if(!bytes)return"0 B";const units=["B","KB","MB","GB","TB"];let n=bytes,i=0;while(n>=1024&&i<units.length-1){n/=1024;i++}return`${n.toFixed(i?1:0)} ${units[i]}`}
function setProgress(job){const percent=Math.max(0,Math.min(100,job.progress||0));progressBar.style.width=`${percent}%`;progressPercent.textContent=`${percent}%`;progressStage.textContent=job.stage||job.status;progressMessage.textContent=job.message||""}
function openProgress(name){progressTitle.textContent=`Backing up ${name}`;progressClose.classList.add("hidden");modal.classList.remove("hidden")}
function sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms))}

async function renderDashboard(){const[containers,backups,info]=await Promise.all([api("/api/containers"),api("/api/backups"),api("/api/info")]);content.innerHTML=`<div class="grid"><article class="card"><h3>${containers.length}</h3><div class="muted">Managed containers</div></article><article class="card"><h3>${backups.length}</h3><div class="muted">Discovered backups</div></article><article class="card"><h3>v${info.version}</h3><div class="muted">ContBak version</div></article></div>`}
async function renderContainers(){const items=await api("/api/containers");content.innerHTML=`<div class="grid">${items.map(c=>`<article class="card"><h3>${c.name}</h3><div class="muted">${c.image}</div><span class="status">${c.status}</span><div class="actions"><button class="backup-button" onclick="backup('${c.id}','${c.name.replaceAll("'","")}')">Backup now</button></div></article>`).join("")}</div>`}
async function renderBackups(){const items=await api("/api/backups");if(!items.length){content.innerHTML='<div class="empty">No backups found in /backups.</div>';return}content.innerHTML=`<table><thead><tr><th>Container</th><th>Created</th><th>Status</th><th>Size</th><th></th></tr></thead><tbody>${items.map(b=>`<tr><td>${b.container_name}</td><td>${new Date(b.created_at).toLocaleString()}</td><td>${b.status}</td><td>${size(b.size)}</td><td><button class="danger" onclick='removeBackup(${JSON.stringify(b.backup_id)})'>Delete</button></td></tr>`).join("")}</tbody></table>`}
async function render(){clearMessage();document.querySelector("#title").textContent=currentView[0].toUpperCase()+currentView.slice(1);try{if(currentView==="containers")await renderContainers();else if(currentView==="backups")await renderBackups();else await renderDashboard()}catch(error){showMessage(error.message,true);content.innerHTML=""}}

async function backup(id,name){
  if(activeJob)return;
  document.querySelectorAll(".backup-button").forEach(button=>button.disabled=true);
  openProgress(name);
  try{
    activeJob=await api("/api/backups",{method:"POST",body:JSON.stringify({container_id:id})});
    setProgress(activeJob);
    while(activeJob.status==="queued"||activeJob.status==="running"){
      await sleep(700);
      activeJob=await api(`/api/jobs/${activeJob.id}`);
      setProgress(activeJob);
    }
    if(activeJob.status==="failed")throw new Error(activeJob.error||activeJob.message||"Backup failed.");
    currentView="backups";
    document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x.dataset.view==="backups"));
    await renderBackups();
    showMessage(`Backup of ${name} completed.`);
    progressClose.classList.remove("hidden");
  }catch(error){showMessage(error.message,true);progressStage.textContent="Failed";progressMessage.textContent=error.message;progressClose.classList.remove("hidden")}
  finally{activeJob=null;document.querySelectorAll(".backup-button").forEach(button=>button.disabled=false)}
}
async function removeBackup(id){if(!confirm("Delete this backup?"))return;try{await api(`/api/backups/${encodeURI(id)}`,{method:"DELETE"});await renderBackups()}catch(error){showMessage(error.message,true)}}

document.querySelectorAll(".nav").forEach(button=>button.addEventListener("click",()=>{currentView=button.dataset.view;document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x===button));render()}));
document.querySelector("#refresh").addEventListener("click",render);
progressClose.addEventListener("click",()=>modal.classList.add("hidden"));
render();
