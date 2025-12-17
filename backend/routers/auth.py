from datetime import datetime, timedelta
from typing import Annotated

import jwt
from jwt import PyJWTError

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from core.schemas import CreateUserRequest, Token
from core.config import (
    SECRET_KEY,
    algorithm as ALGORITHM,
    token_expire_minutes as ACCESS_TOKEN_EXPIRE_MINUTES,
)
from db.database import get_db
from models.user import User

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

router = APIRouter(prefix="/auth", tags=["auth"])

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

db_dependency = Annotated[Session, Depends(get_db)]

# --------------------------------------------------
# PASSWORD HELPERS
# --------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return bcrypt_context.hash(password)


# --------------------------------------------------
# AUTH HELPERS
# --------------------------------------------------


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    username: str,
    user_id: int,
    expires_delta: timedelta,
) -> str:
    now = datetime.utcnow()
    expire = now + expires_delta

    payload = {
        "sub": username,
        "user_id": user_id,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


# --------------------------------------------------
# ROUTES
# --------------------------------------------------


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    create_user_request: CreateUserRequest,
    db: db_dependency,
):
    existing_user = (
        db.query(User)
        .filter(
            (User.username == create_user_request.username)
            | (User.email == create_user_request.email)
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )

    user = User(
        username=create_user_request.username,
        email=create_user_request.email,
        hashed_password=get_password_hash(create_user_request.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User created successfully"}


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
):
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        username=user.username,
        user_id=user.id,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# --------------------------------------------------
# DEPENDENCY
# --------------------------------------------------


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: db_dependency,
) -> User:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        username: str | None = payload.get("sub")
        user_id: int | None = payload.get("user_id")

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )

    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
