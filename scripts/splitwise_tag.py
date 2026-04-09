#!/usr/bin/env python3
"""Tag finance transactions that correspond to Splitwise expenses.

Fetches expenses from the Splitwise API, matches them against existing
bank transactions in the finance DB by (date, amount, currency), and
tags matches with 'splitwise'.

Idempotent: uses ON CONFLICT DO NOTHING on (raw_transaction_id, tag).

Usage:
    python splitwise_tag.py                    # full history
    python splitwise_tag.py --since 2024-01-01 # expenses after date
    python splitwise_tag.py --dry-run          # match only, no writes
    python splitwise_tag.py --dry-run --verbose
"""

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2
from splitwise import Splitwise

from config.settings import settings


def fetch_expenses(since: date | None = None) -> list[dict]:
    """Fetch Splitwise expenses where the current user paid something.

    Returns normalised dicts with: splitwise_id, date, paid_amount,
    owed_amount, currency, description.
    """
    s = Splitwise(
        settings.splitwise_consumer_key,
        settings.splitwise_consumer_secret,
        api_key=settings.splitwise_api_key,
    )
    current_user = s.getCurrentUser()
    user_id = current_user.getId()
    print(f"  Splitwise user: {current_user.getFirstName()} (id={user_id})")

    expenses = []
    offset = 0
    limit = 200

    while True:
        kwargs = {"offset": offset, "limit": limit}
        if since:
            kwargs["dated_after"] = since.isoformat()

        page = s.getExpenses(**kwargs)
        if not page:
            break

        for exp in page:
            # Skip deleted
            if exp.getDeletedAt() is not None:
                continue

            # Skip settlements (inter-user payments)
            if exp.getPayment():
                continue

            # Find current user's share
            for eu in exp.getUsers():
                if eu.getId() == user_id:
                    try:
                        paid = Decimal(eu.getPaidShare())
                    except (InvalidOperation, TypeError):
                        paid = Decimal("0")

                    if paid <= 0:
                        break

                    try:
                        owed = Decimal(eu.getOwedShare())
                    except (InvalidOperation, TypeError):
                        owed = Decimal("0")

                    # Parse date (YYYY-MM-DDT...)
                    date_str = exp.getDate()
                    exp_date = date.fromisoformat(date_str[:10])

                    expenses.append({
                        "splitwise_id": exp.getId(),
                        "date": exp_date,
                        "paid_amount": paid,
                        "owed_amount": owed,
                        "currency": exp.getCurrencyCode(),
                        "description": exp.getDescription() or "",
                    })
                    break

        if len(page) < limit:
            break
        offset += limit

    return expenses


def find_matches(cur, expense_date: date, amount: Decimal, currency: str) -> list[dict]:
    """Find active transactions matching date (+/-2 days) and amount.

    Two strategies:
      1. Direct: currency + amount match on the transaction itself.
      2. Local currency: for FX transactions (e.g. Monzo paying in GBP for a EUR expense),
         match on raw_data->>'local_currency' and raw_data->>'local_amount' (stored in pence).
    """
    date_lo = expense_date - timedelta(days=2)
    date_hi = expense_date + timedelta(days=2)
    neg_amount = -abs(amount)

    # Strategy 1: direct currency + amount match
    cur.execute("""
        SELECT id, posted_at, amount, currency, raw_merchant, institution
        FROM active_transaction
        WHERE currency = %s
          AND amount = %s
          AND posted_at BETWEEN %s AND %s
    """, (currency, neg_amount, date_lo, date_hi))
    cols = [d[0] for d in cur.description]
    results = [dict(zip(cols, row)) for row in cur.fetchall()]

    if results:
        return results

    # Strategy 2: match via raw_data local_currency / local_amount (Monzo FX)
    # local_amount is in minor units (pence/cents), negative for outflows
    local_minor = int(neg_amount * 100)
    cur.execute("""
        SELECT id, posted_at, amount, currency, raw_merchant, institution
        FROM active_transaction
        WHERE raw_data->>'local_currency' = %s
          AND (raw_data->>'local_amount')::int = %s
          AND posted_at BETWEEN %s AND %s
    """, (currency, local_minor, date_lo, date_hi))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def tag_transaction(cur, raw_transaction_id, dry_run: bool = False) -> bool:
    """Insert 'splitwise' tag. Returns True if newly inserted."""
    if dry_run:
        return True

    cur.execute("""
        INSERT INTO transaction_tag (raw_transaction_id, tag, source)
        VALUES (%s, 'splitwise', 'splitwise')
        ON CONFLICT (raw_transaction_id, tag) DO NOTHING
        RETURNING raw_transaction_id
    """, (str(raw_transaction_id),))
    return cur.fetchone() is not None


def process_expenses(expenses: list[dict], conn, dry_run: bool, verbose: bool) -> dict:
    """Match expenses to bank transactions and tag matches."""
    cur = conn.cursor()
    stats = {"matched": 0, "already_tagged": 0, "ambiguous": 0, "unmatched": 0}
    ambiguous_details = []
    unmatched_details = []

    for exp in expenses:
        matches = find_matches(cur, exp["date"], exp["paid_amount"], exp["currency"])

        if len(matches) == 1:
            m = matches[0]
            was_new = tag_transaction(cur, m["id"], dry_run=dry_run)
            if was_new:
                stats["matched"] += 1
            else:
                stats["already_tagged"] += 1

            if verbose:
                status = "MATCH" if was_new else "ALREADY"
                print(f"    [{status}] {exp['date']} {exp['paid_amount']:>8} {exp['currency']} "
                      f"'{exp['description'][:40]}' -> {m['institution']} '{m['raw_merchant']}'")

        elif len(matches) == 0:
            stats["unmatched"] += 1
            unmatched_details.append(exp)
            if verbose:
                print(f"    [UNMATCHED] {exp['date']} {exp['paid_amount']:>8} {exp['currency']} "
                      f"'{exp['description'][:40]}'")

        else:
            stats["ambiguous"] += 1
            ambiguous_details.append({"expense": exp, "candidates": len(matches)})
            if verbose:
                print(f"    [AMBIGUOUS x{len(matches)}] {exp['date']} {exp['paid_amount']:>8} "
                      f"{exp['currency']} '{exp['description'][:40]}'")

    if not dry_run:
        conn.commit()

    return {**stats, "ambiguous_details": ambiguous_details, "unmatched_details": unmatched_details}


def main():
    parser = argparse.ArgumentParser(description="Tag finance transactions matching Splitwise expenses")
    parser.add_argument("--since", help="Only fetch expenses after this date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Match and report only, no DB writes")
    parser.add_argument("--verbose", action="store_true", help="Show every expense match result")
    args = parser.parse_args()

    since = None
    if args.since:
        since = date.fromisoformat(args.since)

    print("=== Splitwise Tagger ===\n")

    # Fetch from Splitwise
    print("Step 1: Fetching expenses from Splitwise...")
    expenses = fetch_expenses(since=since)
    print(f"  Expenses where you paid: {len(expenses)}")

    if not expenses:
        print("\n  No expenses to process.")
        return

    # Date range info
    dates = [e["date"] for e in expenses]
    print(f"  Date range: {min(dates)} to {max(dates)}")

    # Connect and match
    print("\nStep 2: Matching against finance DB...")
    conn = psycopg2.connect(settings.dsn)
    try:
        result = process_expenses(expenses, conn, dry_run=args.dry_run, verbose=args.verbose)

        # Summary
        print(f"\n=== Summary {'(DRY RUN) ' if args.dry_run else ''}===")
        print(f"  Matched (newly tagged): {result['matched']}")
        print(f"  Already tagged:         {result['already_tagged']}")
        print(f"  Ambiguous (2+ matches): {result['ambiguous']}")
        print(f"  Unmatched:              {result['unmatched']}")

        if result["ambiguous_details"] and not args.verbose:
            print("\n  Ambiguous expenses (use --verbose for inline details):")
            for item in result["ambiguous_details"][:10]:
                exp = item["expense"]
                print(f"    {exp['date']} {exp['paid_amount']:>8} {exp['currency']} "
                      f"'{exp['description'][:50]}' ({item['candidates']} candidates)")

    finally:
        conn.close()

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
