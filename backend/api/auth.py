from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from db.db import async_session_maker
from db.user.dao import UserDAO
from backend.schemas.user import UserCreate, UserOut, Token
from backend.core.security import verify_password, get_password_hash, create_access_token
from backend.core.dependencies import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register(user_data: UserCreate):
    async with async_session_maker() as session:
        # Проверка существования пользователя
        existing = await UserDAO.find_one_or_none(username=user_data.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        existing_email = await UserDAO.find_one_or_none(email=user_data.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        hashed = get_password_hash(user_data.password)
        new_user = await UserDAO.add(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed,
        )
        return new_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    async with async_session_maker() as session:
        user = await UserDAO.find_one_or_none(username=form_data.username)
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)):
    return current_user