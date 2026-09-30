from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.auth.security import verify_password, create_access_token
from app.schemas.auth import Token, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest):
    if payload.username != settings.boe_username or not verify_password(
        payload.password, settings.boe_password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(subject=payload.username)
    return Token(access_token=token)