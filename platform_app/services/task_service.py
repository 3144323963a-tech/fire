import json
from threading import RLock

from platform_app.config import TASKS_FILE
from platform_app.models.task import Task
from platform_app.services.sample_data_service import list_sample_tasks
from platform_app.services.dispatch_service import overlay_dispatches


_lock = RLock()


def _read_records() -> list[dict]:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text("[]\n", encoding="utf-8")
    try:
        data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("tasks.json 格式错误，请修复 JSON 后重启") from exc
    if not isinstance(data, list):
        raise RuntimeError("tasks.json 顶层必须是数组")
    return data


def list_tasks() -> list[dict]:
    with _lock:
        records = _read_records()
    tasks = (
        [Task.from_record(record).to_api() for record in records]
        + list_sample_tasks()
    )
    return overlay_dispatches(tasks)


def create_task(payload: dict) -> dict:
    task = Task.from_payload(payload)
    with _lock:
        records = _read_records()
        records.insert(0, task.to_record())
        temporary = TASKS_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(TASKS_FILE)
    return task.to_api()
