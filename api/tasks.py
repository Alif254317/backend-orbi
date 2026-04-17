from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user_id
from tools.supabase_client import get_supabase

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None


@router.get("")
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_before: Optional[str] = None,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
):
    sb = get_supabase()
    q = sb.table("tasks").select("*").eq("user_id", user_id)
    if status:
        q = q.eq("status", status)
    if priority:
        q = q.eq("priority", priority)
    if due_before:
        q = q.lte("due_date", due_before)
    result = q.order("due_date").order("priority").limit(limit).execute()
    return {"tasks": result.data}


@router.post("")
async def create_task(task: TaskCreate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    if task.priority not in ("low", "medium", "high", "urgent"):
        raise HTTPException(status_code=400, detail="Invalid priority")
    if task.status not in ("pending", "in_progress", "completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Invalid status")
    data = task.model_dump(exclude_none=True)
    data["user_id"] = user_id
    try:
        result = sb.table("tasks").insert(data).execute()
        return {"task": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}")
async def get_task(task_id: str, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    result = (
        sb.table("tasks")
        .select("*")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": result.data}


@router.put("/{task_id}")
async def update_task(task_id: str, updates: TaskUpdate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = updates.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "priority" in data and data["priority"] not in ("low", "medium", "high", "urgent"):
        raise HTTPException(status_code=400, detail="Invalid priority")
    if "status" in data and data["status"] not in ("pending", "in_progress", "completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Invalid status")

    result = (
        sb.table("tasks")
        .update(data)
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": result.data[0]}


@router.delete("/{task_id}")
async def delete_task(task_id: str, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    result = (
        sb.table("tasks")
        .delete()
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": result.data[0]}
