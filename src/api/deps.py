"""Connection pool, auth dependencies."""

from mees_shared.db import get_conn, init_pool as _init_pool, close_pool  # noqa: F401
from mees_shared.auth import CurrentUser, get_current_user as _make_get_user, make_require_admin  # noqa: F401
import mees_shared.db as _db_mod

from config.settings import settings

# App-specific auth dependency
get_current_user = _make_get_user(settings.auth_enabled, settings.dev_user_email)
require_admin = make_require_admin(get_current_user)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_user (
    email TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin'
);
INSERT INTO app_user (email, display_name, role)
VALUES ('stu@mees.st', 'Stu', 'admin')
ON CONFLICT DO NOTHING;

ALTER TABLE trip ADD COLUMN IF NOT EXISTS active boolean NOT NULL DEFAULT false;
ALTER TABLE expense ADD COLUMN IF NOT EXISTS source text DEFAULT 'manual';
ALTER TABLE expense ADD COLUMN IF NOT EXISTS pipeline_ref text;
"""


def init_pool() -> None:
    _init_pool(settings.dsn, settings.db_pool_min, settings.db_pool_max)
    conn = _db_mod.pool.getconn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(_SCHEMA)
    finally:
        _db_mod.pool.putconn(conn)
