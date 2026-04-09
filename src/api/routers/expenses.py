"""Expense CRUD endpoints."""

from __future__ import annotations

from collections import defaultdict
import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import CurrentUser, get_conn, get_current_user

router = APIRouter()


def _rows(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


class ExpenseCreate(BaseModel):
    description: str
    amount: str
    currency: str = "GBP"
    paid_by: int
    date: datetime.date | None = None
    involved: list[int] = []


@router.get("/trips/{slug}/expenses")
def list_expenses(
    slug: str,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM trip WHERE slug = %s", (slug,))
    trip = cur.fetchone()
    if not trip:
        raise HTTPException(404, "Trip not found")
    trip_id = trip[0]

    cur.execute("""
        SELECT e.*, m.name AS paid_by_name
        FROM expense e
        JOIN member m ON m.id = e.paid_by
        WHERE e.trip_id = %s
        ORDER BY e.date DESC, e.created_at DESC
    """, (trip_id,))
    expenses = _rows(cur)

    if not expenses:
        return []

    expense_ids = [e["id"] for e in expenses]
    cur.execute("""
        SELECT es.expense_id, es.member_id, es.amount, m.name AS member_name
        FROM expense_share es
        JOIN member m ON m.id = es.member_id
        WHERE es.expense_id = ANY(%s)
        ORDER BY m.name
    """, (expense_ids,))
    shares = _rows(cur)

    shares_by_expense = defaultdict(list)
    for s in shares:
        shares_by_expense[s["expense_id"]].append(s)

    for e in expenses:
        e["shares"] = shares_by_expense.get(e["id"], [])

    return expenses


@router.post("/trips/{slug}/expenses")
def add_expense(
    slug: str,
    body: ExpenseCreate,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("SELECT id FROM trip WHERE slug = %s", (slug,))
    trip = cur.fetchone()
    if not trip:
        raise HTTPException(404, "Trip not found")
    trip_id = trip[0]

    exp_date = body.date or datetime.date.today()
    involved = body.involved

    if not involved:
        cur.execute("SELECT id FROM member WHERE trip_id = %s", (trip_id,))
        involved = [r[0] for r in cur.fetchall()]

    cur.execute(
        "INSERT INTO expense (trip_id, paid_by, description, amount, currency, date) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (trip_id, body.paid_by, body.description, body.amount, body.currency.upper(), exp_date),
    )
    expense_id = cur.fetchone()[0]

    n = len(involved)
    share = (Decimal(body.amount) / n).quantize(Decimal("0.01"))
    remainder = Decimal(body.amount) - share * n
    for i, mid in enumerate(involved):
        s = share + remainder if i == 0 else share
        cur.execute(
            "INSERT INTO expense_share (expense_id, member_id, amount) VALUES (%s, %s, %s)",
            (expense_id, mid, s),
        )

    conn.commit()
    return {"id": expense_id}


@router.delete("/trips/{slug}/expenses/{expense_id}")
def delete_expense(
    slug: str,
    expense_id: int,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("DELETE FROM expense WHERE id = %s RETURNING id", (expense_id,))
    if not cur.fetchone():
        raise HTTPException(404, "Expense not found")
    conn.commit()
    return {"status": "deleted"}
