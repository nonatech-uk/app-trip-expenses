#!/usr/bin/env python3
"""Dump all Splitwise expenses to CSV."""

import csv
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from splitwise import Splitwise
from config.settings import settings


def main():
    s = Splitwise(
        settings.splitwise_consumer_key,
        settings.splitwise_consumer_secret,
        api_key=settings.splitwise_api_key,
    )
    current_user = s.getCurrentUser()
    user_id = current_user.getId()

    rows = []
    offset = 0
    limit = 200

    while True:
        page = s.getExpenses(offset=offset, limit=limit)
        if not page:
            break

        for exp in page:
            if exp.getDeletedAt() is not None:
                continue

            my_paid = "0"
            my_owed = "0"
            for eu in exp.getUsers():
                if eu.getId() == user_id:
                    my_paid = eu.getPaidShare()
                    my_owed = eu.getOwedShare()
                    break

            rows.append({
                "id": exp.getId(),
                "date": str(exp.getDate())[:10],
                "description": exp.getDescription() or "",
                "cost": exp.getCost(),
                "currency": exp.getCurrencyCode(),
                "my_paid_share": my_paid,
                "my_owed_share": my_owed,
                "is_payment": exp.getPayment(),
                "num_users": len(exp.getUsers()),
            })

        if len(page) < limit:
            break
        offset += limit

    writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    main()
