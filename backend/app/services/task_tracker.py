import json
from datetime import datetime, timezone
from typing import Optional

import redis

from app.config import settings
from app.tasks.celery_app import celery_app

TASK_LIST_KEY = "molluscai:tasks:recent"
MAX_TASKS = 100

_pool: Optional[redis.ConnectionPool] = None


def _r() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL, max_connections=5, decode_responses=True
        )
    return redis.Redis(connection_pool=_pool)


def record_task(task_id: str, task_name: str, args: dict = None) -> None:
    entry = {
        "task_id": task_id,
        "task_name": task_name,
        "args": args or {},
        "state": "PENDING",
        "date_created": now_iso(),
    }
    r = _r()
    r.lpush(TASK_LIST_KEY, json.dumps(entry))
    r.ltrim(TASK_LIST_KEY, 0, MAX_TASKS - 1)


def update_task_state(task_id: str, state: str, result: dict = None) -> None:
    r = _r()
    items = r.lrange(TASK_LIST_KEY, 0, -1)
    for i, raw in enumerate(items):
        entry = json.loads(raw)
        if entry["task_id"] == task_id:
            entry["state"] = state
            if result:
                entry["result"] = result
            entry["date_done"] = now_iso()
            r.lset(TASK_LIST_KEY, i, json.dumps(entry))
            break


def get_recent_tasks(limit: int = 50) -> list:
    r = _r()
    items = r.lrange(TASK_LIST_KEY, 0, limit - 1)
    tasks = []
    for raw in items:
        entry = json.loads(raw)
        tasks.append(_refresh_state(entry))
    return tasks


def get_task(task_id: str) -> Optional[dict]:
    r = _r()
    items = r.lrange(TASK_LIST_KEY, 0, -1)
    for raw in items:
        entry = json.loads(raw)
        if entry["task_id"] == task_id:
            return _refresh_state(entry)
    return None


def get_worker_tasks() -> dict:
    try:
        inspect = celery_app.control.inspect(timeout=2)
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        return {"active": active, "scheduled": scheduled, "reserved": reserved}
    except Exception:
        return {"active": {}, "scheduled": {}, "reserved": {}}


def _refresh_state(entry: dict) -> dict:
    if entry["state"] in ("PENDING", "STARTED", "RETRY"):
        async_result = celery_app.AsyncResult(entry["task_id"])
        current = async_result.state
        if current and current != entry["state"]:
            entry["state"] = current
            if current in ("SUCCESS", "FAILURE"):
                entry["date_done"] = now_iso()
                if current == "SUCCESS" and async_result.result:
                    entry["result"] = _serialize_result(async_result.result)
                elif current == "FAILURE":
                    entry["result"] = {"error": str(async_result.info) if async_result.info else "Unknown error"}
    return entry


def _serialize_result(obj) -> dict:
    if isinstance(obj, dict):
        return obj
    return {"value": str(obj)}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
