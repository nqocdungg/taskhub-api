import hashlib
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

TokenType = Literal["access", "refresh"]

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return str(password_context.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bool(password_context.verify(password, password_hash))
    except (TypeError, ValueError):
        return False


def create_token(subject: int, token_type: TokenType) -> str:
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        "jti": str(uuid4()),
    }
    return str(
        jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
    )


def decode_token(token: str, expected_type: TokenType) -> int:
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as error:
        raise ValueError("Token không hợp lệ hoặc đã hết hạn.") from error

    subject = payload.get("sub")
    token_type = payload.get("type")
    if token_type != expected_type or not isinstance(subject, str):
        raise ValueError("Token không đúng loại.")

    try:
        return int(subject)
    except ValueError as error:
        raise ValueError("Token không có subject hợp lệ.") from error


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
