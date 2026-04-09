"""Balance computation and debt simplification — pure business logic."""

from decimal import Decimal


def fx_rate(from_currency: str, to_currency: str, fx_rates: dict) -> Decimal:
    """Get conversion rate. fx_rates maps currency → base currency rate."""
    if from_currency == to_currency:
        return Decimal("1")
    rate = fx_rates.get(from_currency)
    if rate:
        return Decimal(str(rate))
    return Decimal("1")  # fallback: assume 1:1 if no rate set


def compute_balances(
    members: list[dict],
    expenses: list[dict],
    settlements: list[dict],
    base_currency: str,
    fx_rates: dict,
) -> dict:
    """Compute per-member balances in the trip's base currency.

    Returns {member_id: {"name": str, "balance": Decimal}}
    Positive = owed money, Negative = owes money.
    """
    balances = {m["id"]: {"name": m["name"], "balance": Decimal("0")} for m in members}

    for exp in expenses:
        rate = fx_rate(exp["currency"], base_currency, fx_rates)
        balances[exp["paid_by"]]["balance"] += Decimal(str(exp["amount"])) * rate
        for s in exp["shares"]:
            balances[s["member_id"]]["balance"] -= Decimal(str(s["amount"])) * rate

    for s in settlements:
        rate = fx_rate(s["currency"], base_currency, fx_rates)
        amt = Decimal(str(s["amount"])) * rate
        balances[s["from_member"]]["balance"] += amt
        balances[s["to_member"]]["balance"] -= amt

    for b in balances.values():
        b["balance"] = b["balance"].quantize(Decimal("0.01"))

    return balances


def simplify_debts(balances: dict) -> list[dict]:
    """Compute minimum payment set from balances.

    Returns list of {"from": name, "to": name, "amount": Decimal}
    """
    debtors = []
    creditors = []
    for b in balances.values():
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
