"""Settlement endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


def _rows(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


class SettlementCreate(BaseModel):
    from_member: int
    to_member: int
    amount: str
    currency: str = "GBP"
    date: date | None = None


@router.get("/trips/{slug}/settlements")
def list_settlements(
    slug: str,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM trip WHERE slug = %s", (slug,))
    trip = cur.fetchone()
    if not trip:
        raise HTTPException(404, "Trip not found")

    cur.execute("""
        SELECT s.*, mf.name AS from_name, mt.name AS to_name
        FROM settlement s
        JOIN member mf ON mf.id = s.from_member
        JOIN member mt ON mt.id = s.to_member
        WHERE s.trip_id = %s
        ORDER BY s.date DESC
    """, (trip[0],))
    return _rows(cur)


@router.post("/trips/{slug}/settlements")
def add_settlement(
    slug: str,
    body: SettlementCreate,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM trip WHERE slug = %s", (slug,))
    trip = cur.fetchone()
    if not trip:
        raise HTTPException(404, "Trip not found")

    s_date = body.date or date.today()
    cur.execute(
        "INSERT INTO settlement (trip_id, from_member, to_member, amount, currency, date) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (trip[0], body.from_member, body.to_member, body.amount, body.currency.upper(), s_date),
    )
    conn.commit()
    return {"id": cur.fetchone()[0]}
