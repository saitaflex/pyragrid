"""test_db_both.py — same assertions on SQLite and (optionally) Postgres (§5.12 T1-M4).

Set TEST_DATABASE_URL to also run against Postgres.
"""
import os

import pytest

from app.db import Database
from app.defaults import default_rules


def _make(tmp_path, kind):
    if kind == "sqlite":
        return Database(sqlite_path=str(tmp_path / "both.db"))
    return Database(url=os.environ["TEST_DATABASE_URL"])


PARAMS = ["sqlite"] + (["postgres"] if os.environ.get("TEST_DATABASE_URL") else [])


@pytest.mark.parametrize("kind", PARAMS)
def test_db_contract(tmp_path, kind):
    db = _make(tmp_path, kind)
    # idempotent seed
    db.seed_if_empty()
    db.seed_if_empty()
    assert db.q("select count(*) as n from users")[0]["n"] == 3
    assert len(db.list_assets("demo")) == 20
    assert len(db.list_assets("othercorp")) == 1  # tenant filter

    # rule upsert
    rule = default_rules()[0]
    updated = rule.model_copy(update={"name": "Renamed"})
    db.upsert_rule("demo", updated)
    got = [r for r in db.list_rules("demo") if r.rule_id == rule.rule_id][0]
    assert got.name == "Renamed"

    # first-ack-wins
    db.add_ack("demo", "A_1", "first@demo.eu", "2025-01-01T00:00:00Z")
    db.add_ack("demo", "A_1", "second@demo.eu", "2025-01-02T00:00:00Z")
    assert db.get_ack("demo", "A_1")["acked_by"] == "first@demo.eu"

    # audit autoincrement
    db.add_audit("demo", "2025-01-01T00:00:00Z", "x@demo.eu", "login", "")
    db.add_audit("demo", "2025-01-01T00:01:00Z", "x@demo.eu", "login", "")
    ids = [r["id"] for r in db.list_audit("demo")]
    assert len(set(ids)) == len(ids) and len(ids) >= 2
