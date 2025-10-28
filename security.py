# Tệp: security.py
# Mục đích: Xử lý mọi thứ liên quan đến bảo mật

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import models, crud, schemas
from sqlalchemy.orm import Session
from models import SessionLocal

# 1. Cấu hình "băm" mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Cấu hình "Thẻ từ" (JWT Token)
SECRET_KEY = "DAY_LA_KHOA_BI_MAT_CUC_KY_QUAN_TRONG" # Đổi cái này khi deploy
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # Thẻ từ có hạn 7 ngày

# 3. Các hàm bảo mật
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 4. "Người bảo vệ" đứng gác
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực, vui lòng đăng nhập lại",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    admin = crud.get_admin_by_username(db, username=token_data.username)
    if admin is None:
        raise credentials_exception
    return admin