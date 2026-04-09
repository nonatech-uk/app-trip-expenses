"""Pipeline receipt ingestion endpoint."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request

from config.settings import settings
from src.api.deps import get_conn

router = APIRouter()


@router.post("/expenses/ingest")
async def ingest_expense(
    request: Request,
    conn=Depends(get_conn),
):
    """Accept receipt data from the pipeline and create an expense in the active trip."""
    # Authenticate via pipeline secret
    auth = request.headers.get("Authorization", "")
    if not settings.pipeline_ingest_secret or auth != f"Bearer {settings.pipeline_ingest_secret}":
        raise HTTPException(403, "Invalid pipeline secret")

    body = await request.json()

    cur = conn.cursor()

    # Find active trip
    cur.execute("SELECT id, currency FROM trip WHERE active = true LIMIT 1")
    trip_row = cur.fetchone()
    if not trip_row:
        raise HTTPException(422, "No active trip")
    trip_id, trip_currency = trip_row

    # Dedup via pipeline_ref
    pipeline_ref = body.get("pipeline_envelope_id")
    if pipeline_ref:
        cur.execute("SELECT id FROM expense WHERE pipeline_ref = %s", (pipeline_ref,))
        if cur.fetchone():
            return {"status": "duplicate", "pipeline_ref": pipeline_ref}

    merchant = body.get("merchant", "Unknown")
    amount = body.get("amount")
    currency = body.get("currency", trip_currency)
    exp_date_str = body.get("date")

    if not amount:
        raise HTTPException(400, "amount is required")

    exp_date = date.fromisoformat(exp_date_str) if exp_date_str else date.today()

    # Get all members for equal split
    cur.execute("SELECT id FROM member WHERE trip_id = %s", (trip_id,))
    member_ids = [r[0] for r in cur.fetchall()]
    if not member_ids:
        raise HTTPException(422, "Trip has no members")

    # Default paid_by to first member (trip creator)
    paid_by = member_ids[0]

    cur.execute(
        "INSERT INTO expense (trip_id, paid_by, description, amount, currency, date, source, pipeline_ref) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (trip_id, paid_by, merchant, amount, currency.upper(), exp_date, "pipeline", pipeline_ref),
    )
    expense_id = cur.fetchone()[0]

    # Equal split among all members
    n = len(member_ids)
    share = (Decimal(str(amount)) / n).quantize(Decimal("0.01"))
    remainder = Decimal(str(amount)) - share * n
    for i, mid in enumerate(member_ids):
        s = share + remainder if i == 0 else share
        cur.execute(
            "INSERT INTO expense_share (expense_id, member_id, amount) VALUES (%s, %s, %s)",
            (expense_id, mid, s),
        )

    conn.commit()
    return {"status": "created", "expense_id": expense_id}
