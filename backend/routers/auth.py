"""
Authentication router: register, login, and current-user endpoints.
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from database import get_db
from errors import ConflictError, UnauthorizedError
from models import User
from schemas import UserCreate, UserLogin, Token, UserOut
from security import get_password_hash, verify_password, create_access_token, fetch_current_user
from rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

# Pre-computed bcrypt hash of "dummy" for constant-time login failure
_DUMMY_HASH = "$2b$12$EIx9hO4im1St7uFtCC0zYe4M05Ao6CRKu0VJgPnlLz9xqf4N0AG2S"

def _fetch_current_user(
    user: User = Depends(fetch_current_user),
) -> User:
    """Re-export fetch_current_user for local use."""
    return user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ConflictError(detail="email_already_registered", error_code="email_already_registered")

    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Ensure default VM2026 league exists and auto-join user
    from models import League, LeagueMember
    default_league = db.query(League).filter(League.name == "VM2026").first()
    if not default_league:
        default_league = League(
            name="VM2026",
            invite_code="VM2026",
            is_public=True,
            admin_user_id=user.id,
        )
        db.add(default_league)
        db.commit()
        db.refresh(default_league)
    member = LeagueMember(league_id=default_league.id, user_id=user.id)
    db.add(member)
    db.commit()

    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Always run bcrypt to prevent timing-based email enumeration
        verify_password("dummy", _DUMMY_HASH)
        raise UnauthorizedError(detail="invalid_credentials", error_code="invalid_credentials")

    if not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError(detail="invalid_credentials", error_code="invalid_credentials")

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(_fetch_current_user)):
    """Return the currently authenticated user."""
    return current_user