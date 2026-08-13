from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from db.db import async_session_maker
from db.user.dao import UserDAO
from backend.schemas.user import UserCreate, UserOut, Token
from backend.core.security import verify_password, get_password_hash, create_access_token
from backend.core.dependencies import get_current_user
from pydantic import BaseModel


router = APIRouter()


async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

class TgIdUpdate(BaseModel):
    tg_id: int

@router.put("/update_tg_id")
async def update_tg_id(
    data: TgIdUpdate,
    current_user = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    # Проверка, не занят ли tg_id другим пользователем
    existing = await UserDAO.find_one_or_none(tg_id=data.tg_id)
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="Этот Telegram ID уже привязан к другому аккаунту")
    
    # Принудительно загружаем пользователя в текущую сессию
    user = await session.merge(current_user)   # ← вместо session.add
    user.tg_id = data.tg_id
    await session.commit()
    return {"message": "tg_id updated"}

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
        # Принудительно получаем свежий объект с заполненными полями
        #user = await UserDAO.find_one_or_none(id=new_user.id)
        return new_user #user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print(("1. Получен запрос /login"))
    async with async_session_maker() as session:
        print("2. Сессия создана")
        user = await UserDAO.find_one_or_none(username=form_data.username)
        print("3. Запрос к БД выполнен")
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        print("4. user получен")
        access_token = create_access_token(data={"sub": str(user.id)})
        print("5. access_token получен")
        return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)):
    return current_user