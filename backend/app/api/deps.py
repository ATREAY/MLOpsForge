from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

__all__ = ["get_db", "get_current_user"]

# tokenUrl is only used to populate Swagger UI's "Authorize" dialog; the
# actual login endpoint takes a JSON body, not the OAuth2 form format this
# implies — see app/api/v1/auth.py.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().API_V1_PREFIX}/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(_oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(401, "not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if token is None:
        raise unauthorized

    try:
        user_id = decode_access_token(token)
    except JWTError as exc:
        raise unauthorized from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user
