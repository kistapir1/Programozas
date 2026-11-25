"""Friend request endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user
from database import get_db_connection

router = APIRouter(prefix="/api/friends", tags=["friends"])


def _lock_friend_pair(cur, user_id: int, friend_id: int) -> None:
    cur.execute(
        "SELECT pg_advisory_xact_lock(%s, %s)",
        (min(user_id, friend_id), max(user_id, friend_id)),
    )


def _fetch_all(query: str, params: tuple) -> list[dict]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


@router.get("/requests/incoming")
def get_incoming_requests(user: dict = Depends(get_current_user)):
    return _fetch_all(
        """
        SELECT requester.user_id AS id, requester.username
        FROM friendships
        JOIN users AS requester ON requester.user_id = friendships.user_id
        WHERE friendships.friend_id = %s AND friendships.status = 'pending'
        ORDER BY LOWER(requester.username)
        """,
        (user["user_id"],),
    )


@router.get("/requests/outgoing")
def get_outgoing_requests(user: dict = Depends(get_current_user)):
    return _fetch_all(
        """
        SELECT recipient.user_id AS id, recipient.username
        FROM friendships
        JOIN users AS recipient ON recipient.user_id = friendships.friend_id
        WHERE friendships.user_id = %s AND friendships.status = 'pending'
        ORDER BY LOWER(recipient.username)
        """,
        (user["user_id"],),
    )


@router.get("")
def get_friends(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    return _fetch_all(
        """
        SELECT id, username
        FROM (
            SELECT DISTINCT friend.user_id AS id, friend.username
            FROM friendships
            JOIN users AS friend
              ON friend.user_id = CASE
                  WHEN friendships.user_id = %s THEN friendships.friend_id
                  ELSE friendships.user_id
              END
            WHERE (friendships.user_id = %s OR friendships.friend_id = %s)
              AND friendships.status = 'accepted'
        ) AS accepted_friends
        ORDER BY LOWER(username)
        """,
        (user_id, user_id, user_id),
    )


@router.post("/requests/{friend_id}/accept")
def accept_friend_request(friend_id: int, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            _lock_friend_pair(cur, user_id, friend_id)
            cur.execute(
                """
                UPDATE friendships
                SET status = 'accepted'
                WHERE user_id = %s AND friend_id = %s AND status = 'pending'
                """,
                (friend_id, user_id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="A beérkező barátkérelem nem található.",
                )
        conn.commit()
        return {"message": "A barátkérelem elfogadva."}
    finally:
        conn.close()


@router.delete("/requests/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend_request(friend_id: int, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            _lock_friend_pair(cur, user_id, friend_id)
            cur.execute(
                """
                DELETE FROM friendships
                WHERE status = 'pending'
                  AND ((user_id = %s AND friend_id = %s)
                    OR (user_id = %s AND friend_id = %s))
                """,
                (user_id, friend_id, friend_id, user_id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="A függőben lévő barátkérelem nem található.",
                )
        conn.commit()
    finally:
        conn.close()


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(friend_id: int, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            _lock_friend_pair(cur, user_id, friend_id)
            cur.execute(
                """
                DELETE FROM friendships
                WHERE status = 'accepted'
                  AND ((user_id = %s AND friend_id = %s)
                    OR (user_id = %s AND friend_id = %s))
                """,
                (user_id, friend_id, friend_id, user_id),
            )
            if cur.rowcount == 0:
                conn.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="A barátság nem található.",
                )
        conn.commit()
    finally:
        conn.close()


@router.post("/requests/{friend_id}", status_code=status.HTTP_201_CREATED)
def send_friend_request(friend_id: int, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    if friend_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Saját magadnak nem küldhetsz barátkérelmet.")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            _lock_friend_pair(cur, user_id, friend_id)
            cur.execute(
                "SELECT user_id FROM users WHERE user_id = %s FOR KEY SHARE",
                (friend_id,),
            )
            if cur.fetchone() is None:
                conn.rollback()
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A felhasználó nem található.")

            cur.execute(
                """
                SELECT user_id, friend_id, status
                FROM friendships
                WHERE (user_id = %s AND friend_id = %s)
                   OR (user_id = %s AND friend_id = %s)
                """,
                (user_id, friend_id, friend_id, user_id),
            )
            relationships = cur.fetchall()
            for relationship in relationships:
                if relationship["status"] == "accepted":
                    conn.rollback()
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Már barátok vagytok.")
            for relationship in relationships:
                if relationship["user_id"] == user_id and relationship["status"] == "pending":
                    conn.rollback()
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Már küldtél barátkérelmet ennek a felhasználónak.")
            if relationships:
                conn.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ennek a felhasználónak már van függőben lévő kérelme.")

            cur.execute(
                """
                INSERT INTO friendships (user_id, friend_id, status)
                VALUES (%s, %s, 'pending')
                """,
                (user_id, friend_id),
            )
        conn.commit()
        return {"message": "A barátkérelem elküldve."}
    finally:
        conn.close()
