"""Member management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


class MemberCreate(BaseModel):
    name: str


@router.post("/trips/{slug}/members")
def add_member(
    slug: str,
    body: MemberCreate,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM trip WHERE slug = %s", (slug,))
    trip = cur.fetchone()
    if not trip:
        raise HTTPException(404, "Trip not found")

    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name is required")

    cur.execute(
        "INSERT INTO member (trip_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id",
        (trip[0], name),
    )
    row = cur.fetchone()
    conn.commit()
    return {"id": row[0] if row else None}
