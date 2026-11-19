"""
users.py – Felhasználókeresés a navbar „Felhasználó keresése” mezőjéhez
=======================================================================

Végpont (prefix: /api/users):
  GET /search?q=  – részleges egyezés a felhasználónévre (bejelentkezés kell)

A válasz csak user_id-t és felhasználónevet tartalmaz. Email és jelszóhash
nem hagyja el a szervert. A kereső saját magát nem kapja vissza.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from auth import get_current_user, get_user_repository
from db_user_repository import UserRepository

router = APIRouter(prefix="/api/users", tags=["users"])

SEARCH_LIMIT = 10


class UserSearchHit(BaseModel):
    user_id: int
    username: str


class UserSearchResponse(BaseModel):
    results: list[UserSearchHit]


@router.get("/search", response_model=UserSearchResponse)
def search_users(
    q: str = Query(..., min_length=1, max_length=50),
    user: dict = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repository),
):
    matches = repo.search_by_username(
        q,
        exclude_user_id=user["user_id"],
        limit=SEARCH_LIMIT,
    )
    return UserSearchResponse(
        results=[UserSearchHit(user_id=row["user_id"], username=row["username"]) for row in matches]
    )
