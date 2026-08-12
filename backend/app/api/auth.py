from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.security import get_current_user
from app.database.models import User
from app.database.repositories import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth import create_access_token, hash_password, verify_password
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
def register(request: Request, data: RegisterRequest, db: Session = Depends(db_session)):
    users = UserRepository(db)
    if users.get_by_username(data.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    user = users.create(
        username=data.username,
        password_hash=hash_password(data.password),
        display_name=data.display_name or data.username,
    )
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(
        access_token=token,
        user=UserOut(id=user.id, username=user.username, display_name=user.display_name),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(db_session)):
    users = UserRepository(db)
    user = users.get_by_username(data.username)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(
        access_token=token,
        user=UserOut(id=user.id, username=user.username, display_name=user.display_name),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, username=user.username, display_name=user.display_name)
