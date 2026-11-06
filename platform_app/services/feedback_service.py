import json
from datetime import datetime
from threading import RLock
from uuid import uuid4

from platform_app.config import DATA_DIR


FEEDBACK_FILE = DATA_DIR / "feedback.json"
_lock = RLock()


def list_feedback() -> list[dict]:
    with _lock:
        if not FEEDBACK_FILE.exists():
            return []
        value = json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise RuntimeError("feedback.json 顶层必须是数组")
        return value


def create_feedback(payload: dict, tasks: list[dict]) -> dict:
    task_id = str(payload.get("task_id", "")).strip()
    kind = str(payload.get("kind", "")).strip()
    message = str(payload.get("message", "")).strip()
    task = next((item for item in tasks if item.get("id") == task_id), None)
    if task is None:
        raise ValueError("请选择有效任务")
    if kind not in ("完成反馈", "异常反馈"):
        raise ValueError("反馈类型无效")
    if not message:
        raise ValueError("请填写反馈内容")
    record = {"id": str(uuid4()), "task_id": task_id, "task_name": task["name"], "station": task["station"], "kind": kind, "message": message[:1000], "time": datetime.now().strftime("%H:%M"), "created_at": datetime.now().isoformat(timespec="seconds")}
    with _lock:
        records = list_feedback()
        records.insert(0, record)
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = FEEDBACK_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(FEEDBACK_FILE)
    return record
