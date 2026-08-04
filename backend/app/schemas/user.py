import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    # ADMIN volontairement exclu : l'auto-inscription ne doit permettre que
    # porteur/investisseur. Un compte admin se crée hors ligne (cf.
    # create_admin.py) — jamais via cet endpoint public.
    role: Literal[UserRole.PORTEUR, UserRole.INVESTISSEUR] = UserRole.INVESTISSEUR


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_verified: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
