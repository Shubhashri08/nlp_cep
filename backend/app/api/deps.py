import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.entities import AuditLog, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_exception
    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
    return user


def require_role(*allowed_roles: UserRole):
    """ADMIN always passes; otherwise the user's role must be listed."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != UserRole.ADMIN and current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(r.value for r in allowed_roles) or 'ADMIN'}",
            )
        return current_user
    return role_checker


def audit(db: Session, user: User, action: str, resource_type: str, resource_id=None, details=None, request: Request = None):
    db.add(AuditLog(user_id=user.id if user else None, action=action, resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id is not None else None, details=details,
                    ip_address=request.client.host if request and request.client else None))
