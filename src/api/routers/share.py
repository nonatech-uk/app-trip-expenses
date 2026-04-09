"""Public share endpoint — no auth required."""

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_conn
from src.services.balance import compute_balances, simplify_debts

router = APIRouter()


def _rows(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


@router.get("/share/{slug}/{member_id}")
def member_share(
    slug: str,
    member_id: int,
    conn=Depends(get_conn),
):
    """Public read-only view of a member's balance in a trip. No auth required."""
    cur = conn.cursor()

    cur.execute("SELECT * FROM trip WHERE slug = %s", (slug,))
    cols = [d[0] for d in cur.description]
    trip_row = cur.fetchone()
    if not trip_row:
        raise HTTPException(404, "Trip not found")
    trip = dict(zip(cols, trip_row))

    cur.execute("SELECT * FROM member WHERE trip_id = %s ORDER BY name", (trip["id"],))
    members = _rows(cur)

    member = next((m for m in members if m["id"] == member_id), None)
    if not member:
        raise HTTPException(404, "Member not found")

    # Fetch expenses + shares
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
            WHERE es.expense_id = ANY(%s)
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

    my_balance = float(balances.get(member_id, {}).get("balance", 0))
    my_debts = [
        {**d, "amount": float(d["amount"])}
        for d in debts
        if d["from"] == member["name"] or d["to"] == member["name"]
    ]

    my_expenses = []
    for exp in expenses:
        share = next((s for s in exp["shares"] if s["member_id"] == member_id), None)
        if share or exp["paid_by"] == member_id:
            my_expenses.append({**exp, "my_share": float(share["amount"]) if share else 0})

    return {
        "trip": {"name": trip["name"], "currency": trip["currency"]},
        "member": member,
        "balance": my_balance,
        "debts": my_debts,
        "expenses": my_expenses,
    }
