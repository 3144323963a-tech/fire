import json

from platform_app.config import SAMPLE_DATA_DIR


def read_sample_file(name: str) -> list[dict]:
    path = SAMPLE_DATA_DIR / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path.name} 格式错误，请检查 sample_data 文件") from exc
    if not isinstance(value, list):
        raise RuntimeError(f"{path.name} 顶层必须是 JSON 数组")
    return value


def list_sample_tasks() -> list[dict]:
    from platform_app.models.task import Task

    routes = {row.get("route_id"): row for row in read_sample_file("routes.json")}
    tasks = [Task.from_record(row).to_api() for row in read_sample_file("tasks.json")]
    for task in tasks:
        task["route"] = routes.get(task.get("route_id"))
    return tasks


def get_overview() -> dict:
    from platform_app.services.dispatch_service import resources_with_dispatches

    resources = read_sample_file("resources.json")
    return {
        "stations": read_sample_file("stations.json"),
        "resources": resources_with_dispatches(resources),
        "alarms": read_sample_file("alarms.json"),
    }
