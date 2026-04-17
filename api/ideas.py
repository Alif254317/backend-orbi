from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from tools.ideas import structure_idea
from tools.supabase_client import get_supabase

router = APIRouter(prefix="/api/ideas", tags=["ideas"])


class IdeaCapture(BaseModel):
    user_id: str
    raw_text: str
    source: str = "text"  # 'text' or 'voice'


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None
    is_archived: Optional[bool] = None


@router.get("")
async def list_ideas(
    user_id: str = Query(...),
    category: Optional[str] = None,
    tag: Optional[str] = None,
    archived: bool = False,
    limit: int = 100,
):
    sb = get_supabase()
    q = sb.table("ideas").select("*").eq("user_id", user_id).eq("is_archived", archived)
    if category:
        q = q.eq("category", category)
    if tag:
        q = q.contains("tags", [tag.lower()])
    result = q.order("created_at", desc=True).limit(limit).execute()
    return {"ideas": result.data}


@router.post("/capture")
async def capture(payload: IdeaCapture):
    """Structure raw text into a card using LLM and save."""
    if not payload.raw_text or not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text is required")
    if payload.source not in ("text", "voice"):
        raise HTTPException(status_code=400, detail="source must be 'text' or 'voice'")

    structured = structure_idea(payload.raw_text)
    sb = get_supabase()
    data = {
        "user_id": payload.user_id,
        "title": structured["title"],
        "content": structured["content"],
        "raw_text": payload.raw_text,
        "tags": structured["tags"],
        "category": structured["category"],
        "source": payload.source,
    }
    try:
        result = sb.table("ideas").insert(data).execute()
        return {"idea": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{idea_id}")
async def get_idea(idea_id: str, user_id: str = Query(...)):
    sb = get_supabase()
    result = (
        sb.table("ideas")
        .select("*")
        .eq("id", idea_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"idea": result.data}


@router.put("/{idea_id}")
async def update_idea(idea_id: str, updates: IdeaUpdate, user_id: str = Query(...)):
    sb = get_supabase()
    data = updates.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = (
        sb.table("ideas")
        .update(data)
        .eq("id", idea_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"idea": result.data[0]}


@router.delete("/{idea_id}")
async def delete_idea(idea_id: str, user_id: str = Query(...)):
    sb = get_supabase()
    result = (
        sb.table("ideas")
        .delete()
        .eq("id", idea_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"deleted": result.data[0]}
