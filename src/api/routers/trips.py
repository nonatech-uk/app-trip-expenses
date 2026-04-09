"""Trip CRUD endpoints."""

import re

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _rows(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _row(cur):
    cols = [d[0] for d in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else None


class TripCreate(BaseModel):
    name: str
    currency: str = "GBP"
    members: list[str] = []


class FxUpdate(BaseModel):
    fx_rates: dict[str, float]


@router.get("/trips")
def list_trips(
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, count(m.id) AS member_count,
               (SELECT count(*) FROM expense e WHERE e.trip_id = t.id) AS expense_count
        FROM trip t
        LEFT JOIN member m ON m.trip_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """)
    return _rows(cur)


@router.post("/trips")
def create_trip(
    body: TripCreate,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    slug = _slugify(body.name)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trip (name, slug, currency, fx_rates) VALUES (%s, %s, %s, %s) RETURNING id",
        (body.name, slug, body.currency.upper(), psycopg2.extras.Json({})),
    )
    trip_id = cur.fetchone()[0]
    for mname in body.members:
        mname = mname.strip()
        if mname:
            cur.execute("INSERT INTO member (trip_id, name) VALUES (%s, %s)", (trip_id, mname))
    conn.commit()
    return {"id": trip_id, "slug": slug}


@router.get("/trips/{slug}")
def get_trip(
    slug: str,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("SELECT * FROM trip WHERE slug = %s", (slug,))
    trip = _row(cur)
    if not trip:
        raise HTTPException(404, "Trip not found")

    cur.execute("SELECT * FROM member WHERE trip_id = %s ORDER BY name", (trip["id"],))
    trip["members"] = _rows(cur)
    return trip


@router.put("/trips/{slug}/fx")
def update_fx(
    slug: str,
    body: FxUpdate,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute(
        "UPDATE trip SET fx_rates = %s WHERE slug = %s RETURNING id",
        (psycopg2.extras.Json(body.fx_rates), slug),
    )
    if not cur.fetchone():
        raise HTTPException(404, "Trip not found")
    conn.commit()
    return {"status": "updated"}


@router.put("/trips/{slug}/active")
def set_active(
    slug: str,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    """Set this trip as the active trip (for pipeline ingestion). Deactivates all others."""
    cur = conn.cursor()
    cur.execute("UPDATE trip SET active = false WHERE active = true")
    cur.execute("UPDATE trip SET active = true WHERE slug = %s RETURNING id", (slug,))
    if not cur.fetchone():
        raise HTTPException(404, "Trip not found")
    conn.commit()
    return {"status": "activated"}
