CREATE TABLE trip (
    id          serial PRIMARY KEY,
    name        text NOT NULL,
    slug        text NOT NULL UNIQUE,
    currency    char(3) NOT NULL DEFAULT 'GBP',
    fx_rates    jsonb NOT NULL DEFAULT '{}',  -- e.g. {"EUR": 0.84, "CHF": 0.90} → 1 EUR = 0.84 GBP
    active      boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE member (
    id          serial PRIMARY KEY,
    trip_id     integer NOT NULL REFERENCES trip(id),
    name        text NOT NULL,
    email       text,
    UNIQUE (trip_id, name)
);

CREATE TABLE expense (
    id          serial PRIMARY KEY,
    trip_id     integer NOT NULL REFERENCES trip(id),
    paid_by     integer NOT NULL REFERENCES member(id),
    description text NOT NULL,
    amount      numeric(12,2) NOT NULL,
    currency    char(3) NOT NULL,
    date        date NOT NULL DEFAULT CURRENT_DATE,
    source      text DEFAULT 'manual',      -- manual | pipeline
    pipeline_ref text,                       -- pipeline envelope ID for dedup
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE expense_share (
    id          serial PRIMARY KEY,
    expense_id  integer NOT NULL REFERENCES expense(id) ON DELETE CASCADE,
    member_id   integer NOT NULL REFERENCES member(id),
    amount      numeric(12,2) NOT NULL,
    UNIQUE (expense_id, member_id)
);

CREATE TABLE settlement (
    id          serial PRIMARY KEY,
    trip_id     integer NOT NULL REFERENCES trip(id),
    from_member integer NOT NULL REFERENCES member(id),
    to_member   integer NOT NULL REFERENCES member(id),
    amount      numeric(12,2) NOT NULL,
    currency    char(3) NOT NULL,
    date        date NOT NULL DEFAULT CURRENT_DATE,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_member_trip ON member(trip_id);
CREATE INDEX idx_expense_trip ON expense(trip_id);
CREATE INDEX idx_expense_share_expense ON expense_share(expense_id);
CREATE INDEX idx_settlement_trip ON settlement(trip_id);
