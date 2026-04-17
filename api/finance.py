from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user_id
from tools.supabase_client import get_supabase

router = APIRouter(prefix="/api/finance", tags=["finance"])


class TransactionCreate(BaseModel):
    type: str
    amount: float
    description: Optional[str] = None
    category_id: Optional[str] = None
    date: Optional[str] = None


class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    date: Optional[str] = None


@router.get("/categories")
async def list_categories(type: Optional[str] = None, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    q = sb.table("finance_categories").select("*").or_(
        f"user_id.eq.{user_id},is_default.eq.true"
    )
    if type:
        q = q.eq("type", type)
    result = q.order("name").execute()
    return {"categories": result.data}


@router.get("/transactions")
async def list_transactions(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    category_id: Optional[str] = None,
    limit: int = 200,
    user_id: str = Depends(get_current_user_id),
):
    sb = get_supabase()
    q = (
        sb.table("finance_transactions")
        .select("*, finance_categories(name, icon, color)")
        .eq("user_id", user_id)
    )
    if date_from:
        q = q.gte("date", date_from)
    if date_to:
        q = q.lte("date", date_to)
    if type:
        q = q.eq("type", type)
    if category_id:
        q = q.eq("category_id", category_id)
    result = q.order("date", desc=True).limit(limit).execute()
    return {"transactions": result.data}


@router.post("/transactions")
async def create_transaction(tx: TransactionCreate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = tx.model_dump(exclude_none=True)
    data["user_id"] = user_id
    if data.get("type") not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="type must be income or expense")
    if data["amount"] < 0:
        data["amount"] = abs(data["amount"])
    try:
        result = sb.table("finance_transactions").insert(data).execute()
        return {"transaction": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/transactions/{tx_id}")
async def update_transaction(tx_id: str, updates: TransactionUpdate, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    data = updates.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = (
        sb.table("finance_transactions")
        .update(data)
        .eq("id", tx_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"transaction": result.data[0]}


@router.delete("/transactions/{tx_id}")
async def delete_transaction(tx_id: str, user_id: str = Depends(get_current_user_id)):
    sb = get_supabase()
    result = (
        sb.table("finance_transactions")
        .delete()
        .eq("id", tx_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"deleted": result.data[0]}


@router.get("/summary")
async def summary(
    period: str = Query("month", regex="^(today|week|month|year)$"),
    user_id: str = Depends(get_current_user_id),
):
    sb = get_supabase()
    today = date.today()
    if period == "today":
        date_from = today
    elif period == "week":
        date_from = today - timedelta(days=7)
    elif period == "year":
        date_from = today.replace(month=1, day=1)
    else:
        date_from = today.replace(day=1)

    result = (
        sb.table("finance_transactions")
        .select("type, amount, category_id, finance_categories(name, icon, color)")
        .eq("user_id", user_id)
        .gte("date", date_from.isoformat())
        .execute()
    )

    income = 0.0
    expense = 0.0
    by_category: dict[str, dict] = {}
    for t in result.data:
        amt = float(t["amount"])
        if t["type"] == "income":
            income += amt
        else:
            expense += amt
        cat = t.get("finance_categories") or {}
        cat_name = cat.get("name") or "Sem categoria"
        key = f"{t['type']}:{cat_name}"
        if key not in by_category:
            by_category[key] = {
                "type": t["type"],
                "category": cat_name,
                "icon": cat.get("icon"),
                "color": cat.get("color"),
                "total": 0.0,
            }
        by_category[key]["total"] += amt

    return {
        "period": period,
        "date_from": date_from.isoformat(),
        "income": income,
        "expense": expense,
        "balance": income - expense,
        "by_category": list(by_category.values()),
    }
