"""Password hashing and JWT issuance/verification.

Uses the `bcrypt` package directly rather than passlib's CryptContext wrapper
— passlib's bcrypt handler probes `bcrypt.__about__.__version__`, which recent
bcrypt releases (>=4.1) removed, making CryptContext noisy/unreliable. Talking
to bcrypt directly sidesteps that entirely for a use case this simple.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """Returns the subject (user id). Raises jose.JWTError on invalid/expired tokens."""
    settings = get_settings()
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return payload["sub"]
