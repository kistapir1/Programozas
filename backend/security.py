"""
security.py – Jelszó-hash-elés (Argon2id) és JWT token kezelés
================================================================

Jelszavak:
  - Argon2id algoritmus (argon2-cffi), az OWASP elsődleges ajánlása.
  - A salt-ot a könyvtár minden hash-hez véletlenszerűen generálja, és
    a paraméterekkel együtt egyetlen stringben tárolja, pl.:
      $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
    Így a users.password_hash oszlopba elég ezt az egy stringet menteni.
  - needs_rehash(): ha később szigorítjuk a paramétereket, a régi hash-eket
    belépéskor automatikusan újra lehet hash-elni (migráció nélkül).

Tokenek:
  - HS256-tal aláírt JWT, lejárati idővel.
  - A titkos kulcs a JWT_SECRET környezeti változóból jön. Ha nincs megadva,
    indításkor generálunk egy véletlen kulcsot (fejlesztéshez megfelel, de
    ilyenkor újraindítás után minden kiadott token érvénytelenné válik).
"""

import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# =============================================================================
# JELSZÓ-HASH-ELÉS
# =============================================================================

# Az argon2-cffi alapértelmezései az RFC 9106 "low memory" profilját követik:
# time_cost=3, memory_cost=64 MiB, parallelism=4, 16 bájtos salt, 32 bájtos hash.
_password_hasher = PasswordHasher()

# Előre kiszámolt hash egy véletlen jelszóhoz. Akkor ellenőrzünk ellene, ha a
# felhasználó nem létezik, így a válaszidő alapján nem lehet kitalálni,
# hogy egy felhasználónév / email regisztrálva van-e (timing attack).
_DUMMY_HASH = _password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    """Jelszó hash-elése Argon2id-vel. Az eredmény tartalmazza a salt-ot és a paramétereket."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """True, ha a jelszó egyezik a tárolt hash-sel. Hibás formátumú hash esetén is False."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy_password(password: str) -> None:
    """Nem létező felhasználónál hívjuk, hogy a válaszidő ugyanannyi legyen, mint létezőnél."""
    verify_password(password, _DUMMY_HASH)


def password_needs_rehash(password_hash: str) -> bool:
    """True, ha a hash a jelenleginél gyengébb paraméterekkel készült."""
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


# =============================================================================
# JWT TOKENEK
# =============================================================================

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

_jwt_secret = os.getenv("JWT_SECRET")
if not _jwt_secret:
    warnings.warn(
        "JWT_SECRET nincs beállítva – véletlen kulcsot használunk. "
        "Újraindítás után a kiadott tokenek érvénytelenek lesznek. "
        "Éles környezetben mindenképp állítsd be!",
        RuntimeWarning,
    )
    _jwt_secret = secrets.token_urlsafe(64)
JWT_SECRET: str = _jwt_secret


class InvalidTokenError(Exception):
    """Lejárt, hamisított vagy hibás formátumú token."""


def create_access_token(user_id: int, username: str) -> str:
    """Aláírt JWT a felhasználó azonosítójával és lejárati idővel."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # a JWT szabvány szerint a "sub" string
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Ellenőrzi a token aláírását és lejáratát, és visszaadja a user_id-t."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],  # fix lista: kizárja az "alg: none" támadást
            options={"require": ["exp", "iat", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as e:
        raise InvalidTokenError(str(e)) from e
