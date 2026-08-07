from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return check_password_hash(hashed_password, plain_password)

def get_password_hash(password: str) -> str:
    return generate_password_hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_KEY, algorithm=settings.JWT_ALG)

def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_KEY, algorithms=[settings.JWT_ALG])
        return payload
    except JWTError:
        return None