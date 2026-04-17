from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from tools.supabase_client import get_supabase

router = APIRouter(prefix="/api/agenda", tags=["agenda"])


class EventCreate(BaseModel):
    title: str
    start_at: str
    description: Optional[str] = None
    end_at: Optional[str] = None
    location: Optional[str] = None
    reminder_minutes: int = 30
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    reminder_minutes: Optional[int] = None
    is_completed: Optional[bool] = None


@router.get("/events")
async def list_events(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
):
    sb = get_supabase()
    q = sb.table("events").select("*").eq("user_id", user_id)
    if date_from:
        q = q.gte("start_at", date_from)
    if date_to:
        q = q.lte("start_at", date_to)
    result = q.order("start_at").limit(limit).execute()
    return {"events": result.data}


@router.get("/events/today")
async def today_events(user_id: str = Depends(get_current_user_id)):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    return await list_events(
        user_id=user_id,
        date_from=today.isoformat(),
        date_to=tomorrow.isoformat(),
    )


@router.post("/events")
async def create_event(event: EventCreate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = event.model_dump(exclude_none=True)
    data["user_id"] = user_id
    try:
        result = sb.table("events").insert(data).execute()
        return {"event": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events/{event_id}")
async def get_event(event_id: str, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    result = (
        sb.table("events")
        .select("*")
        .eq("id", event_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"event": result.data}


@router.put("/events/{event_id}")
async def update_event(event_id: str, updates: EventUpdate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = updates.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        result = (
            sb.table("events")
            .update(data)
            .eq("id", event_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"event": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    result = (
        sb.table("events")
        .delete()
        .eq("id", event_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"deleted": result.data[0]}
