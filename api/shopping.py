from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user_id
from tools.supabase_client import get_supabase

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


class ListCreate(BaseModel):
    name: str = "Minha Lista"


class ListUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class ItemCreate(BaseModel):
    list_id: str
    name: str
    quantity: int = 1
    unit: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    is_checked: Optional[bool] = None


@router.get("/lists")
async def list_lists(only_active: bool = True, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    q = sb.table("shopping_lists").select("*").eq("user_id", user_id)
    if only_active:
        q = q.eq("is_active", True)
    result = q.order("created_at", desc=True).execute()
    return {"lists": result.data}


@router.post("/lists")
async def create_list(payload: ListCreate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = payload.model_dump()
    data["user_id"] = user_id
    result = sb.table("shopping_lists").insert(data).execute()
    return {"list": result.data[0]}


@router.put("/lists/{list_id}")
async def update_list(list_id: str, updates: ListUpdate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = updates.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = (
        sb.table("shopping_lists")
        .update(data)
        .eq("id", list_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="List not found")
    return {"list": result.data[0]}


@router.delete("/lists/{list_id}")
async def delete_list(list_id: str, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    result = (
        sb.table("shopping_lists")
        .delete()
        .eq("id", list_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="List not found")
    return {"deleted": result.data[0]}


def _verify_list_ownership(sb, list_id: str, user_id: str):
    result = (
        sb.table("shopping_lists")
        .select("id")
        .eq("id", list_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="List not found")


@router.get("/items")
async def list_items(
    list_id: str = Query(...),
    show_checked: bool = True,
    user_id: str = Depends(get_current_user_id),
):
    sb = get_supabase()
    _verify_list_ownership(sb, list_id, user_id)
    q = sb.table("shopping_items").select("*").eq("list_id", list_id)
    if not show_checked:
        q = q.eq("is_checked", False)
    result = q.order("created_at").execute()
    return {"items": result.data}


@router.post("/items")
async def create_item(payload: ItemCreate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    _verify_list_ownership(sb, payload.list_id, user_id)
    data = payload.model_dump(exclude_none=True)
    result = sb.table("shopping_items").insert(data).execute()
    return {"item": result.data[0]}


@router.put("/items/{item_id}")
async def update_item(item_id: str, updates: ItemUpdate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = updates.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    item_check = (
        sb.table("shopping_items")
        .select("list_id")
        .eq("id", item_id)
        .maybe_single()
        .execute()
    )
    if not item_check.data:
        raise HTTPException(status_code=404, detail="Item not found")
    _verify_list_ownership(sb, item_check.data["list_id"], user_id)

    result = sb.table("shopping_items").update(data).eq("id", item_id).execute()
    return {"item": result.data[0]}


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    item_check = (
        sb.table("shopping_items")
        .select("list_id")
        .eq("id", item_id)
        .maybe_single()
        .execute()
    )
    if not item_check.data:
        raise HTTPException(status_code=404, detail="Item not found")
    _verify_list_ownership(sb, item_check.data["list_id"], user_id)

    result = sb.table("shopping_items").delete().eq("id", item_id).execute()
    return {"deleted": result.data[0]}
