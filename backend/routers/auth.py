"""
Authentication router: register, login, and current-user endpoints.
"""
import base64

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from errors import ConflictError, UnauthorizedError, ValidationError
from models import User
from schemas import UserCreate, UserLogin, UserProfileUpdate, Token, UserOut
from security import get_password_hash, verify_password, create_access_token, fetch_current_user
from rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

# Pre-computed bcrypt hash of "dummy" for constant-time login failure
_DUMMY_HASH = "$2b$12$EIx9hO4im1St7uFtCC0zYe4M05Ao6CRKu0VJgPnlLz9xqf4N0AG2S"
_ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_AVATAR_BYTES = 1_000_000

def _fetch_current_user(
    user: User = Depends(fetch_current_user),
) -> User:
    """Re-export fetch_current_user for local use."""
    return user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    email = payload.email.lower()
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        raise ConflictError(detail="email_already_registered", error_code="email_already_registered")

    from models import League, LeagueMember

    try:
        user = User(
            email=email,
            password_hash=get_password_hash(payload.password),
            display_name=payload.display_name,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
        db.add(user)
        db.flush()

        default_league = db.query(League).filter(League.name == "VM2026").first()
        if not default_league:
            default_league = League(
                name="VM2026",
                invite_code="VM2026",
                is_public=True,
                admin_user_id=user.id,
            )
            db.add(default_league)
            db.flush()
        member = LeagueMember(league_id=default_league.id, user_id=user.id)
        db.add(member)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(detail="email_already_registered", error_code="email_already_registered")
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    email = payload.email.lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if not user:
        # Always run bcrypt to prevent timing-based email enumeration
        verify_password("dummy", _DUMMY_HASH)
        raise UnauthorizedError(detail="invalid_credentials", error_code="invalid_credentials")

    if not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError(detail="invalid_credentials", error_code="invalid_credentials")

    if user.email != email:
        user.email = email
        db.commit()

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(_fetch_current_user)):
    """Return the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(_fetch_current_user),
    db: Session = Depends(get_db),
):
    """Update profile identity fields for the current user."""
    email = payload.email.lower()
    display_name = payload.display_name.strip()
    if not display_name:
        raise ValidationError(detail="nickname_required", error_code="nickname_required")

    existing = (
        db.query(User)
        .filter(func.lower(User.email) == email, User.id != current_user.id)
        .first()
    )
    if existing:
        raise ConflictError(detail="email_already_registered", error_code="email_already_registered")

    current_user.email = email
    current_user.first_name = payload.first_name.strip() or None
    current_user.last_name = payload.last_name.strip() or None
    current_user.display_name = display_name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(_fetch_current_user),
    db: Session = Depends(get_db),
):
    """Store a small user-uploaded avatar as a data URL."""
    if file.content_type not in _ALLOWED_AVATAR_TYPES:
        raise ValidationError(detail="avatar_file_type_not_supported", error_code="avatar_file_type_not_supported")

    content = await file.read(_MAX_AVATAR_BYTES + 1)
    if len(content) > _MAX_AVATAR_BYTES:
        raise ValidationError(detail="avatar_file_too_large", error_code="avatar_file_too_large")

    encoded = base64.b64encode(content).decode("ascii")
    current_user.avatar_url = f"data:{file.content_type};base64,{encoded}"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me/avatar", response_model=UserOut)
def delete_avatar(
    current_user: User = Depends(_fetch_current_user),
    db: Session = Depends(get_db),
):
    """Remove the current user's uploaded avatar."""
    current_user.avatar_url = None
    db.commit()
    db.refresh(current_user)
    return current_user
