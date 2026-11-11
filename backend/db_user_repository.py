"""
db_user_repository.py – PostgreSQL alapú UserRepository implementáció
A users táblát kezeli (schema.sql 16. tábla).

Kis- és nagybetűk:
  - Az emailt mindig kisbetűsítve mentjük és keressük.
  - A felhasználónevet a megadott formában mentjük (megjelenítéshez),
    de keresni és egyediséget ellenőrizni kisbetűtől függetlenül kell
    (a schema.sql-ben ehhez van egy LOWER(username) egyedi index is).
"""

from typing import Optional, Protocol

import psycopg2
from psycopg2 import errors

from database import get_db_connection


class UserAlreadyExistsError(Exception):
    """A felhasználónév vagy az email már foglalt."""

    def __init__(self, field: str):
        super().__init__(field)
        self.field = field  # "username" vagy "email"


class UserRepository(Protocol):
    def find_by_username(self, username: str) -> Optional[dict]: ...
    def find_by_email(self, email: str) -> Optional[dict]: ...
    def find_by_id(self, user_id: int) -> Optional[dict]: ...
    def create_user(self, username: str, email: str, password_hash: str) -> dict: ...
    def update_password_hash(self, user_id: int, password_hash: str) -> None: ...


_USER_COLUMNS = "user_id, username, email, password_hash, created_at"


class DbUserRepository:
    """Valódi adatbázis implementáció a UserRepository protokollhoz."""

    def _fetch_one(self, query: str, params: tuple) -> Optional[dict]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            conn.close()

    def find_by_username(self, username: str) -> Optional[dict]:
        return self._fetch_one(
            f"SELECT {_USER_COLUMNS} FROM users WHERE LOWER(username) = LOWER(%s)",
            (username,),
        )

    def find_by_email(self, email: str) -> Optional[dict]:
        return self._fetch_one(
            f"SELECT {_USER_COLUMNS} FROM users WHERE email = LOWER(%s)",
            (email,),
        )

    def find_by_id(self, user_id: int) -> Optional[dict]:
        return self._fetch_one(
            f"SELECT {_USER_COLUMNS} FROM users WHERE user_id = %s",
            (user_id,),
        )

    def create_user(self, username: str, email: str, password_hash: str) -> dict:
        # Előzetes ellenőrzés, hogy pontos hibaüzenetet tudjunk adni
        if self.find_by_username(username):
            raise UserAlreadyExistsError("username")
        if self.find_by_email(email):
            raise UserAlreadyExistsError("email")

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (%s, LOWER(%s), %s)
                    RETURNING {_USER_COLUMNS}
                    """,
                    (username, email, password_hash),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)
        except errors.UniqueViolation as e:
            # Versenyhelyzet: két kérés egyszerre regisztrál ugyanazzal az adattal
            conn.rollback()
            constraint = (e.diag.constraint_name or "").lower()
            raise UserAlreadyExistsError("email" if "email" in constraint else "username") from e
        except psycopg2.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
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
