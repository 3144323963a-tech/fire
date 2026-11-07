"""Example network that scores which devices should take a task.

The weights are fixed. This is not a trained model and it does not call an
external API. Hard limits (offline, maintenance, missing capability, drone
weather) are applied before the network and cannot be overridden.
"""

from __future__ import annotations

from math import exp

from platform_app.services.planning_service import evaluate_candidate


# wind, precip, flight_allowed, battery, idle, capability, terrain, type_match,
# drone, drone_wind, drone_precip
FEATURE_NAMES = (
    "wind",
    "precip",
    "flight_allowed",
    "battery",
    "idle",
    "capability",
    "terrain",
    "type_match",
    "drone",
    "drone_wind",
    "drone_precip",
)

# Two-layer example: hidden readiness, weather, passage, and battery.
HIDDEN_WEIGHTS = (
    (0.0, 0.0, 0.0, 2.4, 0.8, 1.6, 3.4, 1.2, 0.0, 0.0, 0.0),
    (-0.3, 0.0, 1.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -11.0, -9.0),
    (0.0, 0.0, 0.0, 0.0, 0.0, 1.8, 4.4, 1.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0, 14.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
)
HIDDEN_BIAS = (-5.2, 2.2, -4.0, -11.2)
OUTPUT_WEIGHTS = (1.8, 1.6, 2.6, 3.4)
OUTPUT_BIAS = -6.15
THRESHOLD = 0.80
MAX_TEAM = 2


def _sigmoid(value: float) -> float:
    if value >= 0:
        exponent = exp(-value)
        return 1.0 / (1.0 + exponent)
    exponent = exp(value)
    return exponent / (1.0 + exponent)


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def feature_vector(task: dict, resource: dict, environment: dict, result) -> list[float]:
    weather = (environment or {}).get("weather") or {}
    wind = _clip(float(weather.get("wind_mps") or 0) / 12)
    precip = _clip(float(weather.get("precipitation_mm") or 0) / 5)
    flight = 1.0 if (environment or {}).get("flight_allowed", True) else 0.0
    power = resource.get("power_percent")
    battery = 1.0 if power is None else _clip(float(power) / 100)
    idle = 1.0 if resource.get("status") in {"待命", "在线"} else 0.0
    rejected = list(result.rejected_by)
    capability = 0.0 if any(reason.startswith("缺少能力") for reason in rejected) else 1.0
    terrain_blocked = any(reason.startswith("不支持") or reason in {"最大爬坡角不足", "所需通道宽度不足"} for reason in rejected)
    terrain = 0.0 if terrain_blocked else 1.0
    type_match = 0.0 if "设备类型与任务不匹配" in rejected else 1.0
    drone = 1.0 if resource.get("type") == "drone" else 0.0
    return [wind, precip, flight, battery, idle, capability, terrain, type_match, drone, drone * wind, drone * precip]


def forward(features: list[float]) -> float:
    hidden = []
    for weights, bias in zip(HIDDEN_WEIGHTS, HIDDEN_BIAS):
        total = bias + sum(weight * value for weight, value in zip(weights, features))
        hidden.append(_sigmoid(total))
    logit = OUTPUT_BIAS + sum(weight * value for weight, value in zip(OUTPUT_WEIGHTS, hidden))
    return _sigmoid(logit)


def hard_reasons(resource: dict, result) -> list[str]:
    blocked = []
    for reason in result.rejected_by:
        if reason in {"设备非空闲或不在线", "设备不在任务场站"} or reason.startswith("缺少能力"):
            blocked.append(reason)
        elif resource.get("type") == "drone" and (
            reason.startswith("风速") or reason.startswith("降水") or reason.startswith("当前空域")
        ):
            blocked.append(reason)
    return blocked


def score_candidates(task: dict, resources: list[dict], environment: dict, used_ids: set[str] | None = None) -> list[dict]:
    used_ids = used_ids or set()
    scored = []
    for resource in resources:
        result = evaluate_candidate(task, resource, environment)
        blocked = hard_reasons(resource, result)
        if resource.get("id") in used_ids:
            blocked.append("已分配给其他任务")
        features = feature_vector(task, resource, environment, result)
        probability = 0.0 if blocked else forward(features)
        scored.append(
            {
                "resource": resource,
                "result": result,
                "probability": probability,
                "hard_blocked": blocked,
                "features": features,
            }
        )
    return scored


def choose_team(task: dict, resources: list[dict], environment: dict, used_ids: set[str] | None = None) -> list[dict]:
    eligible = [row for row in score_candidates(task, resources, environment, used_ids) if not row["hard_blocked"]]
    eligible.sort(key=lambda row: (-row["probability"], str(row["resource"].get("id"))))
    return [row for row in eligible if row["probability"] >= THRESHOLD][:MAX_TEAM]


def team_reason(picks: list[dict], environment: dict) -> str:
    weather = (environment or {}).get("weather") or {}
    wind = float(weather.get("wind_mps") or 0)
    precip = float(weather.get("precipitation_mm") or 0)
    flight = "允许飞行" if (environment or {}).get("flight_allowed", True) else "禁止飞行"
    names = "、".join(f"{row['resource'].get('name')}（{row['probability'] * 100:.0f}%）" for row in picks)
    terrain_note = "地形和通道过得去" if all(row["features"][6] >= 1 for row in picks) else "部分设备地形受限，只留下过得去的"
    battery_note = "电量更高的优先"
    if any(row["resource"].get("type") == "drone" for row in picks) and wind >= 3:
        battery_note = "有风，只留下电量足够的无人机"
    elif len(picks) == 1:
        battery_note = "其余设备电量或地形概率不够，只出任一台"
    return f"调度判断：风速 {wind:.1f} m/s，降水 {precip:.0f} mm，{flight}。{terrain_note}，{battery_note}。出任 {names}。"
