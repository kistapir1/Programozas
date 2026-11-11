"""
test_auth.py – Tesztek a jelszó-hash-eléshez, a tokenekhez és az auth végpontokhoz
==================================================================================

STUB: StubUserRepository – memóriában tárolja a felhasználókat,
      így nem kell élő adatbázis a tesztekhez.

Futtatás (a backend mappából):
    pip install -r requirements.txt -r requirements-dev.txt
    pytest test_auth.py -v
"""

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("JWT_SECRET", "teszt-titkos-kulcs-csak-tesztekhez-1234567890")

import jwt
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from auth import get_user_repository
from db_user_repository import UserAlreadyExistsError
from main import app
from security import (
    JWT_ALGORITHM,
    JWT_SECRET,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)

# =============================================================================
# STUB
# =============================================================================

class StubUserRepository:
    def __init__(self):
        self.users: dict[int, dict] = {}
        self._next_id = 1

    def find_by_username(self, username):
        return next((u for u in self.users.values() if u["username"].lower() == username.lower()), None)

    def find_by_email(self, email):
        return next((u for u in self.users.values() if u["email"] == email.lower()), None)

    def find_by_id(self, user_id):
        return self.users.get(user_id)

    def create_user(self, username, email, password_hash):
        if self.find_by_username(username):
            raise UserAlreadyExistsError("username")
        if self.find_by_email(email):
            raise UserAlreadyExistsError("email")
        user = {
            "user_id": self._next_id,
            "username": username,
            "email": email.lower(),
            "password_hash": password_hash,
            "created_at": datetime.now(),
        }
        self.users[self._next_id] = user
        self._next_id += 1
        return user

    def update_password_hash(self, user_id, password_hash):
        self.users[user_id]["password_hash"] = password_hash


@pytest.fixture
def repo():
    return StubUserRepository()


@pytest.fixture
def client(repo):
    app.dependency_overrides[get_user_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client, username="teszt_elek", email="Elek@Example.com", password="nagyonTitkos123", again=None):
    return client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "passwordAgain": password if again is None else again,
    })


# =============================================================================
# JELSZÓ-HASH-ELÉS
# =============================================================================

def test_hash_nem_tartalmazza_a_jelszot_es_argon2id():
    h = hash_password("nagyonTitkos123")
    assert "nagyonTitkos123" not in h
    assert h.startswith("$argon2id$")


def test_ugyanaz_a_jelszo_mas_hasht_ad_salt_miatt():
    assert hash_password("ugyanaz123") != hash_password("ugyanaz123")


def test_helyes_es_hibas_jelszo_ellenorzese():
    h = hash_password("nagyonTitkos123")
    assert verify_password("nagyonTitkos123", h)
    assert not verify_password("nagyonTitkos124", h)
    assert not verify_password("", h)


def test_hibas_formatumu_hash_nem_dob_kivetelt():
    assert not verify_password("barmi", "ez-nem-egy-hash")


def test_ekezetes_es_hosszu_jelszo():
    jelszo = "Árvíztűrő tükörfúrógép " * 5  # bcrypt 72 bájtnál levágná, Argon2 nem
    h = hash_password(jelszo)
    assert verify_password(jelszo, h)
    assert not verify_password(jelszo[:-1], h)


def test_gyenge_parameteru_hash_rehash_igenyes():
    gyenge = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("x")
    assert password_needs_rehash(gyenge)
    assert not password_needs_rehash(hash_password("x"))


# =============================================================================
# TOKENEK
# =============================================================================

def test_token_oda_vissza():
    assert decode_access_token(create_access_token(42, "valaki")) == 42


def test_lejart_token_ervenytelen():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": "1", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_mas_kulccsal_alairt_token_ervenytelen():
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "iat": now, "exp": now + timedelta(hours=1)},
                       "hamis-kulcs", algorithm=JWT_ALGORITHM)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_alairas_nelkuli_alg_none_token_ervenytelen():
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "iat": now, "exp": now + timedelta(hours=1)}, None, algorithm="none")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


# =============================================================================
# VÉGPONTOK
# =============================================================================

def test_regisztracio_sikeres_es_hash_kerul_a_dbbe(client, repo):
    r = register(client)
    assert r.status_code == 201
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "teszt_elek"
    assert data["user"]["email"] == "elek@example.com"
    assert "password_hash" not in data["user"]

    tarolt = repo.users[1]["password_hash"]
    assert tarolt.startswith("$argon2id$")
    assert verify_password("nagyonTitkos123", tarolt)


def test_regisztracio_nem_egyezo_jelszavak(client):
    assert register(client, again="masvalami123").status_code == 422


def test_regisztracio_tul_rovid_jelszo(client):
    assert register(client, password="rovid").status_code == 422


def test_regisztracio_tul_hosszu_jelszo(client):
    assert register(client, password="a" * 129).status_code == 422


@pytest.mark.parametrize("nev", ["ab", "van szokoz", "kukac@benne", "x" * 51])
def test_regisztracio_ervenytelen_felhasznalonev(client, nev):
    assert register(client, username=nev).status_code == 422


def test_regisztracio_ervenytelen_email(client):
    assert register(client, email="nem-email").status_code == 422


def test_regisztracio_foglalt_nev_kisbetutol_fuggetlenul(client):
    register(client)
    r = register(client, username="TESZT_ELEK", email="masik@example.com")
    assert r.status_code == 409
    assert "felhasználónév" in r.json()["detail"]


def test_regisztracio_foglalt_email(client):
    register(client)
    r = register(client, username="masik", email="ELEK@example.com")
    assert r.status_code == 409
    assert "email" in r.json()["detail"]


@pytest.mark.parametrize("identifier", ["teszt_elek", "Teszt_Elek", "elek@example.com", "  ELEK@Example.com "])
def test_belepes_nevvel_vagy_emaillel(client, identifier):
    register(client)
    r = client.post("/api/auth/login", json={"identifier": identifier, "password": "nagyonTitkos123"})
    assert r.status_code == 200
    assert decode_access_token(r.json()["access_token"]) == 1


def test_belepes_rossz_jelszo_es_nem_letezo_user_ugyanazt_az_uzenetet_adja(client):
    register(client)
    rossz_jelszo = client.post("/api/auth/login", json={"identifier": "teszt_elek", "password": "rossz12345"})
    nincs_ilyen = client.post("/api/auth/login", json={"identifier": "senki", "password": "rossz12345"})
    assert rossz_jelszo.status_code == nincs_ilyen.status_code == 401
    assert rossz_jelszo.json() == nincs_ilyen.json()


def test_belepes_gyenge_hash_automatikusan_frissul(client, repo):
    gyenge = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("regiJelszo123")
    repo.create_user("regi_user", "regi@example.com", gyenge)
    r = client.post("/api/auth/login", json={"identifier": "regi_user", "password": "regiJelszo123"})
    assert r.status_code == 200
    uj = repo.users[1]["password_hash"]
    assert uj != gyenge
    assert not password_needs_rehash(uj)
    assert verify_password("regiJelszo123", uj)


def test_me_tokennel(client):
    token = register(client).json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "teszt_elek"
    assert "password_hash" not in r.json()


def test_me_token_nelkul_es_hibas_tokennel(client):
    assert client.get("/api/auth/me").status_code == 401
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer ez.nem.token"})
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_torolt_felhasznalo_tokenje(client, repo):
    token = register(client).json()["access_token"]
    repo.users.clear()
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
