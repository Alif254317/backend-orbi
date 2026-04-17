from datetime import datetime, date, time as dtime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from tools.supabase_client import get_supabase

router = APIRouter(prefix="/api/routines", tags=["routines"])


class RoutineCreate(BaseModel):
    user_id: str
    title: str
    times: list[str]
    category: str = "other"
    recurrence: str = "daily"
    weekdays: list[int] = [1, 2, 3, 4, 5, 6, 7]
    target_count: Optional[int] = None
    description: Optional[str] = None


class RoutineUpdate(BaseModel):
    title: Optional[str] = None
    times: Optional[list[str]] = None
    category: Optional[str] = None
    recurrence: Optional[str] = None
    weekdays: Optional[list[int]] = None
    target_count: Optional[int] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class LogEntry(BaseModel):
    user_id: str
    scheduled_at: Optional[str] = None
    note: Optional[str] = None
    skipped: bool = False


@router.get("")
async def list_routines(
    user_id: str = Query(...),
    active_only: bool = True,
    category: Optional[str] = None,
):
    sb = get_supabase()
    q = sb.table("routines").select("*").eq("user_id", user_id)
    if active_only:
        q = q.eq("active", True)
    if category:
        q = q.eq("category", category)
    result = q.order("title").execute()
    return {"routines": result.data}


@router.post("")
async def create_routine(payload: RoutineCreate):
    sb = get_supabase()
    data = payload.model_dump(exclude_none=True)
    try:
        result = sb.table("routines").insert(data).execute()
        return {"routine": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/today")
async def today_routines(user_id: str = Query(...)):
    """Return today's routines with per-routine completion count."""
    sb = get_supabase()
    today = date.today()
    weekday = today.isoweekday()

    r_res = (
        sb.table("routines")
        .select("*")
        .eq("user_id", user_id)
        .eq("active", True)
        .execute()
    )
    routines = [r for r in r_res.data if weekday in (r.get("weekdays") or [])]

    start = datetime.combine(today, dtime.min).isoformat()
    end = datetime.combine(today, dtime.max).isoformat()
    logs_res = (
        sb.table("routine_logs")
        .select("routine_id, completed_at")
        .eq("user_id", user_id)
        .gte("scheduled_at", start)
        .lte("scheduled_at", end)
        .execute()
    )

    # Group logs by routine
    by_routine: dict[str, int] = {}
    for l in logs_res.data:
        if l.get("completed_at"):
            by_routine[l["routine_id"]] = by_routine.get(l["routine_id"], 0) + 1

    enriched = []
    for r in routines:
        completed = by_routine.get(r["id"], 0)
        target = r.get("target_count") or len(r.get("times") or [])
        enriched.append({
            **r,
            "completed_count": completed,
            "target": max(target, 1),
            "is_done": completed >= max(target, 1),
        })
    return {"date": today.isoformat(), "routines": enriched}


@router.get("/{routine_id}")
async def get_routine(routine_id: str, user_id: str = Query(...)):
    sb = get_supabase()
    result = (
        sb.table("routines")
        .select("*")
        .eq("id", routine_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Routine not found")
    return {"routine": result.data}


@router.put("/{routine_id}")
async def update_routine(
    routine_id: str,
    updates: RoutineUpdate,
    user_id: str = Query(...),
):
    sb = get_supabase()
    data = updates.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = (
        sb.table("routines")
        .update(data)
        .eq("id", routine_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Routine not found")
    return {"routine": result.data[0]}


@router.delete("/{routine_id}")
async def delete_routine(routine_id: str, user_id: str = Query(...)):
    sb = get_supabase()
    result = (
        sb.table("routines")
        .delete()
        .eq("id", routine_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Routine not found")
    return {"deleted": result.data[0]}


@router.post("/{routine_id}/logs")
async def log_routine(routine_id: str, payload: LogEntry):
    sb = get_supabase()

    # Verify ownership
    r = (
        sb.table("routines")
        .select("id")
        .eq("id", routine_id)
        .eq("user_id", payload.user_id)
        .maybe_single()
        .execute()
    )
    if not r.data:
        raise HTTPException(status_code=404, detail="Routine not found")

    now = datetime.now().isoformat()
    data = {
        "routine_id": routine_id,
        "user_id": payload.user_id,
        "scheduled_at": payload.scheduled_at or now,
        "completed_at": None if payload.skipped else now,
        "skipped": payload.skipped,
    }
    if payload.note:
        data["note"] = payload.note
    result = sb.table("routine_logs").insert(data).execute()
    return {"log": result.data[0]}


@router.get("/{routine_id}/logs")
async def list_logs(
    routine_id: str,
    user_id: str = Query(...),
    days: int = 7,
):
    sb = get_supabase()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    result = (
        sb.table("routine_logs")
        .select("*")
        .eq("routine_id", routine_id)
        .eq("user_id", user_id)
        .gte("scheduled_at", since)
        .order("scheduled_at", desc=True)
        .execute()
    )
    return {"logs": result.data}


@router.delete("/logs/{log_id}")
async def delete_log(log_id: str, user_id: str = Query(...)):
    sb = get_supabase()
    result = (
        sb.table("routine_logs")
        .delete()
        .eq("id", log_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"deleted": result.data[0]}
