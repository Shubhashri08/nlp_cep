from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.api.deps import audit, get_current_user, require_role
from backend.app.core.config import settings
from backend.app.core.security import create_access_token, get_password_hash, verify_password
from backend.app.database.session import get_db
from backend.app.llm.providers import get_llm
from backend.app.models.entities import User, UserRole
from backend.app.schemas.dss_schemas import DemoLoginRequest, Token, UserCreate, UserResponse

router = APIRouter()


def _token_for(user: User) -> dict:
    return {
        "access_token": create_access_token(subject=user.id, role=user.role.value),
        "token_type": "bearer", "role": user.role.value, "user_id": user.id,
        "full_name": user.full_name, "email": user.email,
    }


@router.get("/config")
def public_config():
    """Public, non-sensitive UI configuration."""
    llm = get_llm()
    return {"demo_mode": settings.DEMO_MODE, "llm_provider": llm.name, "llm_model": llm.model or None,
            "city": settings.CITY_NAME, "version": settings.VERSION}


@router.post("/login", response_model=Token)
def login(request: Request, db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username.strip().lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
    audit(db, user, "USER_LOGIN", "AUTH", user.id, {"role": user.role.value}, request)
    db.commit()
    return _token_for(user)


@router.post("/demo-login", response_model=Token)
def demo_login(payload: DemoLoginRequest, request: Request, db: Session = Depends(get_db)):
    """One-click role login for demonstrations. Disabled unless DEMO_MODE=true."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo login is disabled")
    user = db.query(User).filter(User.role == payload.role, User.is_active.is_(True)).order_by(User.id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"No active {payload.role.value} account – run the seed script")
    audit(db, user, "DEMO_LOGIN", "AUTH", user.id, {"role": user.role.value}, request)
    db.commit()
    return _token_for(user)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_role())):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(user_in: UserCreate, request: Request, db: Session = Depends(get_db),
                current_user: User = Depends(require_role())):
    email = user_in.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="User with this email already exists")
    user = User(email=email, hashed_password=get_password_hash(user_in.password), full_name=user_in.full_name,
                role=user_in.role, is_active=True)
    db.add(user)
    db.flush()
    audit(db, current_user, "USER_CREATED", "USER", user.id, {"role": user.role.value}, request)
    db.commit()
    db.refresh(user)
    return user
