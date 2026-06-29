"""
Users router: cached avatar serving.

Avatars are stored as data URIs in the users.avatar_url column.
This endpoint decodes and serves them as raw image bytes with
proper HTTP caching headers so they're fetched once per browser.
"""
import base64
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import User

router = APIRouter(prefix="/users", tags=["users"])

# Browser cache: 7 days. Avatars rarely change, and when they do
# the ETag changes too so the browser re-fetches automatically.
_CACHE_MAX_AGE = 7 * 24 * 3600


@router.get("/{user_id}/avatar")
def get_user_avatar(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Serve a user's avatar image with HTTP cache headers.

    Returns 404 if the user has no avatar — the frontend falls
    back to initials via the UserAvatar component.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar_url:
        raise HTTPException(status_code=404, detail="Avatar not found")

    data_uri = user.avatar_url
    # Parse data:image/png;base64,xxxx → content_type + bytes
    try:
        header, b64data = data_uri.split(",", 1)
        content_type = header.split(":")[1].split(";")[0]
        image_bytes = base64.b64decode(b64data)
    except (ValueError, IndexError):
        raise HTTPException(status_code=404, detail="Avatar not found")

    # ETag from content hash — changes when user uploads a new avatar
    etag = hashlib.sha256(image_bytes).hexdigest()[:16]

    # 304 if browser cache matches
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304, headers={"ETag": f'"{etag}"'})

    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={
            "Cache-Control": f"public, max-age={_CACHE_MAX_AGE}, immutable",
            "ETag": f'"{etag}"',
        },
    )