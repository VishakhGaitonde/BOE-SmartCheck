from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from app.auth.security import verify_password, create_access_token
from app.schemas.auth import Token, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != settings.boe_username or not verify_password(
        form_data.password, settings.boe_password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(subject=form_data.username)
    return Token(access_token=token)