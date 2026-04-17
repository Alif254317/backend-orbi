from datetime import datetime
from typing import Optional

from fastapi import Header, HTTPException, status

from tools.supabase_client import get_supabase


async def get_current_user_id(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Extracts the user_id from either:
    - X-API-Key header (custom key stored in api_keys table)
    - Authorization: Bearer <jwt> (Supabase JWT)
    Raises 401 if neither is valid.
    """
    if x_api_key:
        return _validate_api_key(x_api_key)
    if authorization:
        return _validate_jwt(authorization)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide X-API-Key or Authorization: Bearer <jwt>",
    )


def _validate_api_key(key: str) -> str:
    sb = get_supabase()
    res = (
        sb.table("api_keys")
        .select("user_id, revoked_at")
        .eq("key", key)
        .maybe_single()
        .execute()
    )
    if not res or not res.data or res.data.get("revoked_at"):
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    user_id = res.data["user_id"]
    try:
        sb.table("api_keys").update(
            {"last_used_at": datetime.utcnow().isoformat()}
        ).eq("key", key).execute()
    except Exception:
        pass
    return user_id


def _validate_jwt(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = authorization[7:]
    sb = get_supabase()
    try:
        response = sb.auth.get_user(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    if not response or not response.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return response.user.id
