"""Balance computation + debt simplification endpoint."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import CurrentUser, get_conn, get_current_user
from src.services.balance import compute_balances, simplify_debts

router = APIRouter()


def _rows(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/trips/{slug}/balances")
def get_balances(
    slug: str,
    _user: CurrentUser = Depends(get_current_user),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    cur.execute("SELECT * FROM trip WHERE slug = %s", (slug,))
    cols = [d[0] for d in cur.description]
    trip_row = cur.fetchone()
    if not trip_row:
        raise HTTPException(404, "Trip not found")
    trip = dict(zip(cols, trip_row))

    cur.execute("SELECT * FROM member WHERE trip_id = %s ORDER BY name", (trip["id"],))
    members = _rows(cur)

    # Fetch expenses with shares
    cur.execute("""
        SELECT e.*, m.name AS paid_by_name
        FROM expense e JOIN member m ON m.id = e.paid_by
        WHERE e.trip_id = %s ORDER BY e.date DESC
    """, (trip["id"],))
    expenses = _rows(cur)

    if expenses:
        expense_ids = [e["id"] for e in expenses]
        cur.execute("""
            SELECT es.expense_id, es.member_id, es.amount, m.name AS member_name
            FROM expense_share es JOIN member m ON m.id = es.member_id
            WHERE es.expense_id = ANY(%s) ORDER BY m.name
        """, (expense_ids,))
        shares = _rows(cur)
        shares_by_expense = defaultdict(list)
        for s in shares:
            shares_by_expense[s["expense_id"]].append(s)
        for e in expenses:
            e["shares"] = shares_by_expense.get(e["id"], [])
    else:
        for e in expenses:
            e["shares"] = []

    cur.execute("""
        SELECT s.*, mf.name AS from_name, mt.name AS to_name
        FROM settlement s
        JOIN member mf ON mf.id = s.from_member
        JOIN member mt ON mt.id = s.to_member
        WHERE s.trip_id = %s
    """, (trip["id"],))
    settlements = _rows(cur)

    balances = compute_balances(
        members, expenses, settlements,
        trip["currency"], trip["fx_rates"] or {},
    )
    debts = simplify_debts(balances)

    # Convert Decimal to float for JSON serialization
    for b in balances.values():
        b["balance"] = float(b["balance"])
    for d in debts:
        d["amount"] = float(d["amount"])

    return {"balances": balances, "debts": debts}
