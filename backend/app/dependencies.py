import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_exception

    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise credentials_exception
    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)
) -> User | None:
    """Comme get_current_user, mais renvoie None au lieu de lever une 401
    si aucun token n'est fourni ou s'il est invalide — utilisé pour les
    pages publiques (ex: liste des projets) qui adaptent juste l'affichage
    selon que quelqu'un est connecté ou non."""
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        return None
    return db.get(User, uuid.UUID(payload["sub"]))


def require_role(*allowed_roles: UserRole):
    """Factory de dépendance : restreint un endpoint à certains rôles.

    Exemple : Depends(require_role(UserRole.ADMIN))
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action non autorisée pour ce rôle",
            )
        return current_user

    return checker
