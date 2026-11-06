"""Qwen dispatch planner."""
import json
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from platform_app.services.sample_data_service import get_overview
from platform_app.services.task_service import list_tasks
from platform_app.services.dispatch_service import TASK_TYPE_FOR_RESOURCE,active_dispatches
def U(h):
 h=h.replace(" ","")
 return "".join(chr(int(h[i:i+4],16)) for i in range(0,len(h),4))
API_KEY='sk-ws-H.YRIYXYL.dMPX.MEQCIEB2rwMhlqH2mEnGOuufKRMVTsDt7kVOgpCj3JzQQv9dAiAgpRvePUqcNPd_kwgBLzSR4i8QkVRGimf5IYdMxrZ3Rw'
ENDPOINT="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL="qwen-plus"
def parse_plan(text):
 text=text.strip()
 if text.startswith("```"): text=text.split(chr(10),1)[-1].rsplit("```",1)[0].strip()
 try: obj=json.loads(text)
 except json.JSONDecodeError:
  a,b=text.find("{"),text.rfind("}")
  if a<0 or b<=a: raise RuntimeError("Invalid Qwen JSON")
  obj=json.loads(text[a:b+1])
 if not isinstance(obj,dict) or not isinstance(obj.get("assignments"),list): raise RuntimeError("Invalid Qwen plan format")
 return obj
def create_ai_dispatch_plan():
 tasks=list_tasks(); resources=get_overview().get("resources",[])
 pending=[x for x in tasks if x.get("status") in (U("5f858c035ea6"),U("5f856d5353d1"))]
 available=[x for x in resources if x.get("status") in (U("5f85547d"),U("57287ebf"))]
 busy=active_dispatches(); used_t={x.get("task_id") for x in busy}; used_r={x.get("resource_id") for x in busy}
 pending=[x for x in pending if x.get("id") not in used_t]; available=[x for x in available if x.get("id") not in used_r]
 if not pending: return {"model":MODEL,"summary":U("5f53 524d 6ca1 6709 5f85 8c03 5ea6 4efb 52a1"),"assignments":[],"unmatched_tasks":[]}
 data={"tasks":[{k:t.get(k) for k in ("id","name","type","station","time","points","route_id")} for t in pending],"resources":[{k:r.get(k) for k in ("id","name","type","station","status","task","power")} for r in available],"resource_task_type_map":TASK_TYPE_FOR_RESOURCE}
 prompt="Allocate inspection tasks to heterogeneous resources. Use only input IDs; assign each task and resource at most once. Enforce task type, available status and same station. Prefer higher numeric power among eligible resources. Do not invent metrics. Return JSON summary and assignments(task_id,resource_id,reason). Write summary and reasons in concise Chinese. Leave unmatched tasks unassigned."
 body={"model":MODEL,"temperature":0.2,"messages":[{"role":"system","content":prompt},{"role":"user","content":json.dumps(data,ensure_ascii=False)}]}
 req=Request(ENDPOINT,data=json.dumps(body).encode("utf-8"),headers={"Authorization":"Bearer "+API_KEY,"Content-Type":"application/json"},method="POST")
 try:
  with urlopen(req,timeout=45) as response: result=json.loads(response.read().decode("utf-8"))
 except HTTPError as ex: raise RuntimeError(f"Qwen HTTP {ex.code}: {ex.read().decode('utf-8',errors='replace')[:300]}") from ex
 except (URLError,TimeoutError) as ex: raise RuntimeError(f"Qwen connection failed: {ex}") from ex
 try: content=result["choices"][0]["message"]["content"]
 except (KeyError,IndexError,TypeError) as ex: raise RuntimeError("Qwen response missing content") from ex
 if isinstance(content,list): content="".join(p.get("text","") for p in content if isinstance(p,dict))
 plan=parse_plan(str(content)); tm={str(x["id"]):x for x in pending}; rm={str(x["id"]):x for x in available}; seen_t=set();seen_r=set(); matches=[]
 for row in plan["assignments"]:
  if not isinstance(row,dict): continue
  tid,rid=str(row.get("task_id","")),str(row.get("resource_id","")); t=tm.get(tid);r=rm.get(rid)
  if not t or not r or tid in seen_t or rid in seen_r: continue
  if TASK_TYPE_FOR_RESOURCE.get(r.get("type"))!=t.get("type") or r.get("station")!=t.get("station") or r.get("status") not in (U("5f85547d"),U("57287ebf")): continue
  matches.append({"task_id":tid,"task_name":t["name"],"resource_id":rid,"resource_name":r["name"],"reason":str(row.get("reason",""))[:240]});seen_t.add(tid);seen_r.add(rid)
 return {"model":MODEL,"summary":str(plan.get("summary",""))[:500],"assignments":matches,"unmatched_tasks":[x["id"] for x in pending if x["id"] not in seen_t]}
