"""
auth.py – Regisztráció, belépés és tokenes azonosítás végpontjai
=================================================================

Végpontok (prefix: /api/auth):
  POST /register  – új felhasználó; siker esetén rögtön tokent is ad
  POST /login     – belépés emaillel VAGY felhasználónévvel (identifier)
  GET  /me        – a tokenhez tartozó felhasználó adatai (védett)

A védett végpontok a get_current_user függőséget használják:
    @app.get("/valami")
    def valami(user: dict = Depends(get_current_user)): ...
A frontendnek a tokent így kell küldenie:
    Authorization: Bearer <access_token>
"""

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from db_user_repository import DbUserRepository, UserAlreadyExistsError, UserRepository
from security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    verify_dummy_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

PASSWORD_MIN_LENGTH = 8
# Felső korlát: egy több megabájtos "jelszó" hash-elése feleslegesen terhelné a szervert
PASSWORD_MAX_LENGTH = 128
# A @ tiltott a felhasználónévben, így belépéskor egyértelmű, hogy emailt vagy nevet kaptunk
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]{3,50}$")

INVALID_CREDENTIALS = "Hibás felhasználónév/email vagy jelszó."


# =============================================================================
# KÉRÉS / VÁLASZ MODELLEK
# =============================================================================

class RegisterRequest(BaseModel):
    # A frontend camelCase "passwordAgain" mezőt küld; snake_case-szel is elfogadjuk
    model_config = ConfigDict(populate_by_name=True)

    username: str
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    password_again: str = Field(alias="passwordAgain", max_length=PASSWORD_MAX_LENGTH)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not USERNAME_PATTERN.fullmatch(v):
            raise ValueError(
                "A felhasználónév 3–50 karakter lehet, és csak betűt, számot, "
                "pontot, kötőjelet és aláhúzást tartalmazhat."
            )
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.password_again:
            raise ValueError("A két jelszó nem egyezik.")
        return self


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)  # email vagy felhasználónév
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserOut(BaseModel):
    user_id: int
    username: str
    email: str
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # másodperc
    user: UserOut


# =============================================================================
# FÜGGŐSÉGEK
# =============================================================================

def get_user_repository() -> UserRepository:
    """Tesztekben app.dependency_overrides-szal stubra cserélhető."""
    return DbUserRepository()


_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    repo: UserRepository = Depends(get_user_repository),
) -> dict:
    """A kérés Bearer tokenje alapján visszaadja a bejelentkezett felhasználót, különben 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Érvénytelen vagy lejárt token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise unauthorized
    user = repo.find_by_id(user_id)
    if user is None:  # pl. azóta törölték a fiókot
        raise unauthorized
    return user


def _to_user_out(user: dict) -> UserOut:
    # Szándékosan csak ezeket a mezőket adjuk vissza – a password_hash soha nem hagyja el a szervert
    return UserOut(
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
        created_at=user.get("created_at"),
    )


def _token_response(user: dict) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user["user_id"], user["username"]),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_to_user_out(user),
    )


# =============================================================================
# VÉGPONTOK
# =============================================================================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, repo: UserRepository = Depends(get_user_repository)):
    password_hash = hash_password(body.password)
    try:
        user = repo.create_user(body.username, body.email, password_hash)
    except UserAlreadyExistsError as e:
        message = (
            "Ez a felhasználónév már foglalt."
            if e.field == "username"
            else "Ezzel az email címmel már regisztráltak."
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, repo: UserRepository = Depends(get_user_repository)):
    identifier = body.identifier.strip()
    if "@" in identifier:
        user = repo.find_by_email(identifier.lower())
    else:
        user = repo.find_by_username(identifier)

    if user is None:
        # Ugyanannyi ideig dolgozunk, mintha létezne a felhasználó
        verify_dummy_password(body.password)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)

    # Ha azóta erősebb hash-paraméterekre váltottunk, most frissítjük a tárolt hash-t
    if password_needs_rehash(user["password_hash"]):
        repo.update_password_hash(user["user_id"], hash_password(body.password))

    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    return _to_user_out(user)
