"""Trip expense sharing web app."""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import db

app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


# --- Trip list ---

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    trips = db.get_trips()
    return templates.TemplateResponse("trips.html", {"request": request, "trips": trips})


@app.post("/")
def create_trip(
    request: Request,
    name: str = Form(),
    currency: str = Form(default="GBP"),
    members: str = Form(default=""),
):
    slug = _slugify(name)
    member_names = [m.strip() for m in members.split(",") if m.strip()]
    db.create_trip(name, slug, currency.upper(), member_names)
    return RedirectResponse(f"/t/{slug}", status_code=303)


# --- Trip detail ---

@app.get("/t/{slug}", response_class=HTMLResponse)
def trip_detail(request: Request, slug: str):
    trip = db.get_trip(slug)
    if not trip:
        return HTMLResponse("Trip not found", status_code=404)

    members = db.get_members(trip["id"])
    expenses = db.get_expenses(trip["id"])
    settlements = db.get_settlements(trip["id"])
    balances = db.compute_balances(trip["id"])
    debts = db.simplify_debts(balances)

    return templates.TemplateResponse("trip.html", {
        "request": request,
        "trip": trip,
        "members": members,
        "expenses": expenses,
        "settlements": settlements,
        "balances": balances,
        "debts": debts,
    })


@app.post("/t/{slug}/expense")
def add_expense(
    request: Request,
    slug: str,
    description: str = Form(),
    amount: str = Form(),
    currency: str = Form(default="GBP"),
    paid_by: int = Form(),
    date_str: str = Form(alias="date", default=""),
    involved: list[int] = Form(default=[]),
):
    trip = db.get_trip(slug)
    if not trip:
        return HTMLResponse("Trip not found", status_code=404)

    exp_date = date.fromisoformat(date_str) if date_str else date.today()

    if not involved:
        # Default: everyone
        members = db.get_members(trip["id"])
        involved = [m["id"] for m in members]

    db.add_expense(trip["id"], paid_by, description, amount, currency.upper(), exp_date, involved)
    return RedirectResponse(f"/t/{slug}", status_code=303)


@app.post("/t/{slug}/settle")
def settle(
    request: Request,
    slug: str,
    from_member: int = Form(),
    to_member: int = Form(),
    amount: str = Form(),
    currency: str = Form(default="GBP"),
    date_str: str = Form(alias="date", default=""),
):
    trip = db.get_trip(slug)
    if not trip:
        return HTMLResponse("Trip not found", status_code=404)

    s_date = date.fromisoformat(date_str) if date_str else date.today()
    db.add_settlement(trip["id"], from_member, to_member, amount, currency.upper(), s_date)
    return RedirectResponse(f"/t/{slug}", status_code=303)


@app.post("/t/{slug}/expense/{expense_id}/delete")
def delete_expense(slug: str, expense_id: int):
    db.delete_expense(expense_id)
    return RedirectResponse(f"/t/{slug}", status_code=303)


@app.post("/t/{slug}/member")
def add_member(slug: str, name: str = Form()):
    trip = db.get_trip(slug)
    if trip and name.strip():
        db.add_member(trip["id"], name)
    return RedirectResponse(f"/t/{slug}", status_code=303)


@app.post("/t/{slug}/fx")
async def update_fx(request: Request, slug: str):
    trip = db.get_trip(slug)
    if not trip:
        return HTMLResponse("Trip not found", status_code=404)
    form = await request.form()
    fx_rates = {}
    for key, val in form.items():
        if key.startswith("fx_") and val:
            currency = key[3:]
            fx_rates[currency] = float(val)
    db.update_trip_fx(slug, fx_rates)
    return RedirectResponse(f"/t/{slug}", status_code=303)


# --- Per-person summary ---

@app.get("/t/{slug}/{member_id:int}", response_class=HTMLResponse)
def person_summary(request: Request, slug: str, member_id: int):
    trip = db.get_trip(slug)
    if not trip:
        return HTMLResponse("Trip not found", status_code=404)

    members = db.get_members(trip["id"])
    member = next((m for m in members if m["id"] == member_id), None)
    if not member:
        return HTMLResponse("Member not found", status_code=404)

    expenses = db.get_expenses(trip["id"])
    balances = db.compute_balances(trip["id"])
    debts = db.simplify_debts(balances)

    # Filter expenses this member was involved in
    my_expenses = []
    for exp in expenses:
        share = next((s for s in exp["shares"] if s["member_id"] == member_id), None)
        if share or exp["paid_by"] == member_id:
            my_expenses.append({**exp, "my_share": share["amount"] if share else 0})

    my_balance = balances.get(member_id, {}).get("balance", 0)
    my_debts = [d for d in debts if d["from"] == member["name"] or d["to"] == member["name"]]

    return templates.TemplateResponse("person.html", {
        "request": request,
        "trip": trip,
        "member": member,
        "expenses": my_expenses,
        "balance": my_balance,
        "debts": my_debts,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
