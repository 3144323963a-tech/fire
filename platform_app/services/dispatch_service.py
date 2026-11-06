"""Dispatch validation and one-pass simulated inspections."""
import json
from datetime import datetime,timezone
from threading import RLock
from platform_app.config import DISPATCHES_FILE,SAMPLE_DATA_DIR
from platform_app.services.sample_data_service import get_overview
def U(h):
 h=h.replace(" ","")
 return "".join(chr(int(h[i:i+4],16)) for i in range(0,len(h),4))
_lock=RLock();TASK_TYPE_FOR_RESOURCE={"robot":"robot","dog":"robot","drone":"drone","person":"team"};SIMULATION_DURATION_SECONDS=900
PENDING=U("5f858c035ea6");READY=U("5f85547d");ONLINE=U("57287ebf");SENT=U("5df26d3e53d1");RUNNING=U("6267884c4e2d");DONE=U("5df25b8c6210")
def list_dispatches():
 with _lock:
  if not DISPATCHES_FILE.exists(): return []
  try: value=json.loads(DISPATCHES_FILE.read_text(encoding="utf-8"))
  except json.JSONDecodeError as ex: raise RuntimeError("dispatch history is invalid") from ex
  if not isinstance(value,list): raise RuntimeError("dispatch history must be an array")
  return value
def dispatch_state(row,now=None):
 if row.get("status")!=SENT:return row.get("status",SENT)
 try: started=datetime.fromisoformat(row["created_at"].replace("Z","+00:00"))
 except (KeyError,ValueError):return RUNNING
 elapsed=max(0,((now or datetime.now(timezone.utc))-started).total_seconds())
 return DONE if elapsed>=int(row.get("simulation_duration_seconds",SIMULATION_DURATION_SECONDS)) else RUNNING
def active_dispatches():return [x for x in list_dispatches() if dispatch_state(x) in (SENT,RUNNING)]
def create_dispatch(payload,tasks):
 tid=str(payload.get("task_id","")).strip();rid=str(payload.get("resource_id","")).strip();task=next((x for x in tasks if x.get("id")==tid),None)
 if not task:raise ValueError("Task not found")
 if task.get("status") not in (PENDING,U("5f856d5353d1")):raise ValueError("Task is already dispatched or completed")
 resource=next((x for x in get_overview().get("resources",[]) if x.get("id")==rid),None)
 if not resource:raise ValueError("Resource not found")
 if resource.get("status") not in (READY,ONLINE):raise ValueError("Resource is not available")
 if TASK_TYPE_FOR_RESOURCE.get(resource.get("type"))!=task.get("type"):raise ValueError("Resource type does not match task")
 if resource.get("station")!=task.get("station"):raise ValueError("Resource and task must belong to the same station")
 row={"task_id":tid,"task_name":task["name"],"resource_id":rid,"resource_name":resource["name"],"status":SENT,"created_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"simulation_duration_seconds":SIMULATION_DURATION_SECONDS}
 with _lock:
  history=list_dispatches();active=active_dispatches()
  if any(x.get("resource_id")==rid for x in active):raise ValueError("Resource already has an active task")
  if any(x.get("task_id")==tid for x in active):raise ValueError("Task has already been dispatched")
  history.insert(0,row);DISPATCHES_FILE.parent.mkdir(parents=True,exist_ok=True);temp=DISPATCHES_FILE.with_suffix(".tmp")
  temp.write_text(json.dumps(history,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8");temp.replace(DISPATCHES_FILE)
 return row
def overlay_dispatches(tasks):
 by_task={x["task_id"]:x for x in list_dispatches()}
 for task in tasks:
  row=by_task.get(task.get("id"))
  if not row:continue
  state=dispatch_state(row);task["status"]=state;task["executor"]=row["resource_name"];task["dispatch_started_at"]=row.get("created_at","");task["simulation_duration_seconds"]=int(row.get("simulation_duration_seconds",SIMULATION_DURATION_SECONDS))
  if state==DONE:task["progress"]="100%"
  elif state==RUNNING:
   started=datetime.fromisoformat(row["created_at"].replace("Z","+00:00"));elapsed=max(0,(datetime.now(timezone.utc)-started).total_seconds());task["progress"]=str(min(99,int(elapsed/task["simulation_duration_seconds"]*100)))+"%"
  else:task["progress"]="0%"
 return tasks
def resources_with_dispatches(resources):
 active={x["resource_id"]:x for x in active_dispatches()}
 for resource in resources:
  row=active.get(resource.get("id"))
  if row:resource["status"]=RUNNING;resource["task"]=row.get("task_name","")
 return resources


def reset_dispatch_history():
    with _lock:
        DISPATCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
        DISPATCHES_FILE.write_text("[]" + chr(10), encoding="utf-8")
        resource_file = SAMPLE_DATA_DIR / "resources.json"
        if resource_file.exists():
            rows = json.loads(resource_file.read_text(encoding="utf-8"))
            for row in rows:
                if row.get("status") == RUNNING:
                    row["status"] = READY
                row["task"] = U("5f85 547d")
            resource_file.write_text(json.dumps(rows, ensure_ascii=True, indent=2) + chr(10), encoding="utf-8")
