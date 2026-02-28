# Trip Expenses

Self-hosted expense sharing app + Splitwise-to-finance tagger.

## Trip Expenses Web App

Lightweight Splitwise replacement. Create a trip, add members, log expenses, share a link via WhatsApp — everyone sees what they owe. No app install, no account, no login.

### Run locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --port 8001 --reload
```

Open http://localhost:8001

### Features

- Create trips with members
- Add expenses — choose who paid, who's involved (equal split, uncheck to exclude)
- Multi-currency (EUR, CHF, GBP, PLN, NOK, USD)
- Settle up in GBP using configurable FX rates per trip
- Per-person summary pages — shareable links for WhatsApp
- Record settlements
- Delete expenses

### Database setup

Requires PostgreSQL. Create the database and apply the schema:

```bash
createdb -h 192.168.128.9 -U postgres splitwise
psql -h 192.168.128.9 -U finance -d splitwise -f schema.sql
```

### Configuration

Copy `config/.env.example` to `config/.env`:

```
DB_PASSWORD=your_password
```

The app connects to the `splitwise` database on `192.168.128.9:5432`.

## Splitwise Tagger

Matches Splitwise API expenses against existing bank transactions in the finance system and tags them with `splitwise`.

### Usage

```bash
# Dry run — see what would be tagged
.venv/bin/python splitwise_tag.py --dry-run --verbose

# Tag all matching transactions
.venv/bin/python splitwise_tag.py

# Only expenses after a date
.venv/bin/python splitwise_tag.py --since 2025-01-01
```

### How matching works

1. Fetches expenses from Splitwise where you paid
2. For each expense, searches the finance DB `active_transaction` view:
   - Direct match: same currency, amount, date (±2 days)
   - FX fallback: matches Monzo `raw_data.local_currency` / `local_amount` for foreign transactions
3. Tags exact matches with `splitwise` in `transaction_tag`
4. Idempotent — safe to re-run

### Splitwise API setup

Register an app at https://secure.splitwise.com/apps, then add to `config/.env`:

```
SPLITWISE_CONSUMER_KEY=...
SPLITWISE_CONSUMER_SECRET=...
SPLITWISE_API_KEY=...
```

### Dump expenses

Export all Splitwise expenses to CSV:

```bash
.venv/bin/python dump_expenses.py > expenses.csv
```
