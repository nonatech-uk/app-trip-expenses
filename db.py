"""Database helpers for the trips app."""

import psycopg2
import psycopg2.extras
from collections import defaultdict
from decimal import Decimal

from config.settings import settings

_pool = None


def get_conn():
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.connect(settings.trips_dsn)
    return _pool


def reset_conn():
    global _pool
    if _pool and not _pool.closed:
        _pool.close()
    _pool = None


def _rows(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _row(cur):
    cols = [d[0] for d in cur.description]
    r = cur.fetchone()
    return dict(zip(cols, r)) if r else None


# --- Trips ---

def get_trips():
    conn = get_conn()
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


def get_trip(slug):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trip WHERE slug = %s", (slug,))
    return _row(cur)


def create_trip(name, slug, currency, member_names, fx_rates=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trip (name, slug, currency, fx_rates) VALUES (%s, %s, %s, %s) RETURNING id",
        (name, slug, currency, psycopg2.extras.Json(fx_rates or {})),
    )
    trip_id = cur.fetchone()[0]
    for mname in member_names:
        mname = mname.strip()
        if mname:
            cur.execute(
                "INSERT INTO member (trip_id, name) VALUES (%s, %s)",
                (trip_id, mname),
            )
    conn.commit()
    return trip_id


def update_trip_fx(slug, fx_rates):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE trip SET fx_rates = %s WHERE slug = %s",
        (psycopg2.extras.Json(fx_rates), slug),
    )
    conn.commit()


# --- Members ---

def get_members(trip_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM member WHERE trip_id = %s ORDER BY name", (trip_id,))
    return _rows(cur)


def add_member(trip_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO member (trip_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id",
        (trip_id, name.strip()),
    )
    conn.commit()
    row = cur.fetchone()
    return row[0] if row else None


# --- Expenses ---

def get_expenses(trip_id):
    conn = get_conn()
    cur = conn.cursor()
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


def add_expense(trip_id, paid_by, description, amount, currency, date, member_ids):
    """Add expense split equally among member_ids."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expense (trip_id, paid_by, description, amount, currency, date) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (trip_id, paid_by, description, amount, currency, date),
    )
    expense_id = cur.fetchone()[0]

    n = len(member_ids)
    share = (Decimal(str(amount)) / n).quantize(Decimal("0.01"))
    # Give remainder to first person to ensure shares sum to total
    remainder = Decimal(str(amount)) - share * n
    for i, mid in enumerate(member_ids):
        s = share + remainder if i == 0 else share
        cur.execute(
            "INSERT INTO expense_share (expense_id, member_id, amount) VALUES (%s, %s, %s)",
            (expense_id, mid, s),
        )

    conn.commit()
    return expense_id


def delete_expense(expense_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM expense WHERE id = %s", (expense_id,))
    conn.commit()


# --- Settlements ---

def get_settlements(trip_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, mf.name AS from_name, mt.name AS to_name
        FROM settlement s
        JOIN member mf ON mf.id = s.from_member
        JOIN member mt ON mt.id = s.to_member
        WHERE s.trip_id = %s
        ORDER BY s.date DESC
    """, (trip_id,))
    return _rows(cur)


def add_settlement(trip_id, from_member, to_member, amount, currency, date):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settlement (trip_id, from_member, to_member, amount, currency, date) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (trip_id, from_member, to_member, amount, currency, date),
    )
    conn.commit()
    return cur.fetchone()[0]


# --- Balance computation ---

def compute_balances(trip_id):
    """Compute per-member balances in the trip's base currency.

    Returns {member_id: {"name": str, "balance": Decimal}}
    Positive = owed money, Negative = owes money.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM trip WHERE id = %s", (trip_id,))
    trip = _row(cur)
    base_currency = trip["currency"]
    fx = trip["fx_rates"] or {}

    members = get_members(trip_id)
    balances = {m["id"]: {"name": m["name"], "balance": Decimal("0")} for m in members}

    expenses = get_expenses(trip_id)
    for exp in expenses:
        rate = _fx_rate(exp["currency"], base_currency, fx)
        # Payer gets credit for the full amount
        balances[exp["paid_by"]]["balance"] += Decimal(str(exp["amount"])) * rate
        # Each sharer gets debited their share
        for s in exp["shares"]:
            balances[s["member_id"]]["balance"] -= Decimal(str(s["amount"])) * rate

    settlements = get_settlements(trip_id)
    for s in settlements:
        rate = _fx_rate(s["currency"], base_currency, fx)
        amt = Decimal(str(s["amount"])) * rate
        balances[s["from_member"]]["balance"] += amt
        balances[s["to_member"]]["balance"] -= amt

    # Round
    for b in balances.values():
        b["balance"] = b["balance"].quantize(Decimal("0.01"))

    return balances


def simplify_debts(balances):
    """Compute minimum payment set from balances.

    Returns list of {"from": name, "to": name, "amount": Decimal}
    """
    debtors = []
    creditors = []
    for mid, b in balances.items():
        if b["balance"] < 0:
            debtors.append({"name": b["name"], "amount": -b["balance"]})
        elif b["balance"] > 0:
            creditors.append({"name": b["name"], "amount": b["balance"]})

    debtors.sort(key=lambda x: x["amount"], reverse=True)
    creditors.sort(key=lambda x: x["amount"], reverse=True)

    payments = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        d = debtors[i]
        c = creditors[j]
        pay = min(d["amount"], c["amount"])
        if pay > Decimal("0.01"):
            payments.append({
                "from": d["name"],
                "to": c["name"],
                "amount": pay.quantize(Decimal("0.01")),
            })
        d["amount"] -= pay
        c["amount"] -= pay
        if d["amount"] < Decimal("0.01"):
            i += 1
        if c["amount"] < Decimal("0.01"):
            j += 1

    return payments


def _fx_rate(from_currency, to_currency, fx_rates):
    """Get conversion rate. fx_rates maps currency -> base currency rate."""
    if from_currency == to_currency:
        return Decimal("1")
    rate = fx_rates.get(from_currency)
    if rate:
        return Decimal(str(rate))
    return Decimal("1")  # fallback: assume 1:1 if no rate set
