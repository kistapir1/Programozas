"""
profile.py – A bejelentkezett felhasználó saját profiladatainak módosítása
===========================================================================

Ez a fájl ÖNÁLLÓAN kezeli a felhasználónév és a jelszó módosítását:
a saját validációját és adatbázis-lekérdezéseit is maga tartalmazza,
nem nyúl hozzá az auth.py vagy a db_user_repository.py tartalmához.

A hitelesítéshez (get_current_user) és az alap eszközökhöz (adatbázis-
kapcsolat, jelszó-hash) a meglévő modulokat HASZNÁLJA, de nem MÓDOSÍTJA
őket - ez az egyetlen kapcsolódási pont a meglévő kódhoz.

Végpontok (prefix: /api/profile):
  PATCH /username  – felhasználónév módosítása
  PATCH /password  – jelszó módosítása (a jelenlegi jelszó megadásával)

Bekötés a main.py-ban (ez az egyetlen szükséges módosítás egy meglévő
fájlban):
    from profile import router as profile_router
    app.include_router(profile_router)
"""

import re
from typing import Optional

import psycopg2
from psycopg2 import errors
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from auth import get_current_user
from database import get_db_connection
from security import hash_password, verify_password

router = APIRouter(prefix="/api/profile", tags=["profile"])

# Ugyanazok az értékek, mint az auth.py-ban - szándékosan külön definiálva,
# hogy ez a fájl ne függjön az auth.py belső részleteitől
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]{3,50}$")

_USER_COLUMNS = "user_id, username, email, password_hash, created_at"


class ProfileUsernameConflictError(Exception):
    """A kért felhasználónév már foglalt."""


# =============================================================================
# SAJÁT ADATBÁZIS-MŰVELETEK (nem a db_user_repository.py-t használja)
# =============================================================================

def _find_by_username(username: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_USER_COLUMNS} FROM users WHERE LOWER(username) = LOWER(%s)",
                (username,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def _update_username_in_db(user_id: int, new_username: str) -> dict:
    # Előzetes ellenőrzés a pontos hibaüzenethez
    existing = _find_by_username(new_username)
    if existing and existing["user_id"] != user_id:
        raise ProfileUsernameConflictError()

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE users SET username = %s
                WHERE user_id = %s
                RETURNING {_USER_COLUMNS}
                """,
                (new_username, user_id),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
    except errors.UniqueViolation as e:
        # Versenyhelyzet: valaki közben ugyanerre a névre módosított
        conn.rollback()
        raise ProfileUsernameConflictError() from e
    except psycopg2.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def _update_password_in_db(user_id: int, password_hash: str) -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (password_hash, user_id),
            )
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# KÉRÉS / VÁLASZ MODELLEK
# =============================================================================

class UpdateUsernameRequest(BaseModel):
    username: str

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


class UpdateUsernameResponse(BaseModel):
    user_id: int
    username: str
    email: str


class UpdatePasswordRequest(BaseModel):
    # A frontend camelCase "newPasswordAgain" mezőt küld; snake_case-szel is elfogadjuk
    model_config = ConfigDict(populate_by_name=True)

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    new_password_again: str = Field(alias="newPasswordAgain", max_length=PASSWORD_MAX_LENGTH)

    @model_validator(mode="after")
    def passwords_match(self) -> "UpdatePasswordRequest":
        if self.new_password != self.new_password_again:
            raise ValueError("A két új jelszó nem egyezik.")
        return self


# =============================================================================
# VÉGPONTOK
# =============================================================================

@router.patch("/username", response_model=UpdateUsernameResponse)
def update_username(
    body: UpdateUsernameRequest,
    user: dict = Depends(get_current_user),
):
    try:
        updated = _update_username_in_db(user["user_id"], body.username)
    except ProfileUsernameConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ez a felhasználónév már foglalt.",
        )
    return UpdateUsernameResponse(
        user_id=updated["user_id"],
        username=updated["username"],
        email=updated["email"],
    )


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(
    body: UpdatePasswordRequest,
    user: dict = Depends(get_current_user),
):
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A jelenlegi jelszó helytelen.",
        )
    _update_password_in_db(user["user_id"], hash_password(body.new_password))
