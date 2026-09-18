"""db.py — DB adapter (Postgres or SQLite) + tenant-filtered repository (§5.3).

Same portable SQL on both engines; `?` placeholders converted to `%s` for Postgres.
Every query filters by the caller's customer_id.
"""
from __future__ import annotations

import os
from pathlib import Path

from app.models import Site, SopRule

_DATA = Path(__file__).resolve().parent.parent / "data"


def _sqlite_path() -> str:
    if os.environ.get("VERCEL"):
        return "/tmp/wai.db"
    try:
        _DATA.mkdir(parents=True, exist_ok=True)
        probe = _DATA / ".writetest"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        return str(_DATA / "app.db")
    except OSError:
        return "/tmp/wai.db"


class Database:
    def __init__(self, url: str | None = None, sqlite_path: str | None = None) -> None:
        self.is_pg = bool(url)
        if self.is_pg:
            import psycopg
            from psycopg.rows import dict_row
            self._url = url
            self._conn = psycopg.connect(url, autocommit=True, row_factory=dict_row)
        else:
            import sqlite3
            self.sqlite_path = sqlite_path or _sqlite_path()
            self._conn = sqlite3.connect(self.sqlite_path,
                                         isolation_level=None, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def healthy(self) -> bool:
        try:
            self.q("select 1 as x")
            return True
        except Exception:
            return False

    # -- low level -------------------------------------------------------
    def q(self, sql: str, params: tuple = ()) -> list[dict]:
        stmt = sql.replace("?", "%s") if self.is_pg else sql
        try:
            cur = self._conn.cursor()
            cur.execute(stmt, params)
        except Exception:
            if self.is_pg:  # reconnect once on a dropped connection
                import psycopg
                from psycopg.rows import dict_row
                self._conn = psycopg.connect(self._url, autocommit=True, row_factory=dict_row)
                cur = self._conn.cursor()
                cur.execute(stmt, params)
            else:
                raise
        if cur.description:
            return [dict(r) for r in cur.fetchall()]
        return []

    def _create_schema(self) -> None:
        auto = "bigserial primary key" if self.is_pg else "integer primary key autoincrement"
        self.q("create table if not exists users(email text primary key, name text, "
               "customer_id text, role text, salt text, hash text)")
        self.q("create table if not exists assets(customer_id text, site_id text, data text, "
               "primary key(customer_id, site_id))")
        self.q("create table if not exists sop_rules(customer_id text, rule_id text, data text, "
               "primary key(customer_id, rule_id))")
        self.q("create table if not exists acks(customer_id text, alert_id text, acked_by text, "
               "acked_at text, primary key(customer_id, alert_id))")
        self.q(f"create table if not exists audit(id {auto}, customer_id text, at text, "
               "actor text, action text, details text)")
        self.q("create table if not exists advisor_suggestions(customer_id text, "
               "suggestion_id text, incident_id text, data text, created_at text, "
               "primary key(customer_id, suggestion_id))")
        self.q("create table if not exists advisor_decisions(customer_id text, "
               "suggestion_id text, decision text, note text, decided_by text, "
               "decided_at text, primary key(customer_id, suggestion_id))")

    # -- seed ------------------------------------------------------------
    def seed_if_empty(self) -> None:
        if self.q("select count(*) as n from users")[0]["n"] > 0:
            return
        from app.auth import hash_password
        from app.defaults import DEMO_USERS, default_rules, othercorp_site
        from app.importer import seed_sites
        for email, name, cid, role, pw in DEMO_USERS:
            salt, h = hash_password(pw)
            self.q("insert into users(email,name,customer_id,role,salt,hash) "
                   "values(?,?,?,?,?,?) on conflict do nothing",
                   (email, name, cid, role, salt, h))
        for s in seed_sites():
            self.q("insert into assets(customer_id,site_id,data) values(?,?,?) "
                   "on conflict do nothing", ("demo", s.site_id, s.model_dump_json()))
        oc = othercorp_site()
        self.q("insert into assets(customer_id,site_id,data) values(?,?,?) "
               "on conflict do nothing", ("othercorp", oc.site_id, oc.model_dump_json()))
        for cid in ("demo", "othercorp"):
            for r in default_rules():
                self.q("insert into sop_rules(customer_id,rule_id,data) values(?,?,?) "
                       "on conflict do nothing", (cid, r.rule_id, r.model_dump_json()))

    # -- users -----------------------------------------------------------
    def get_user(self, email: str) -> dict | None:
        rows = self.q("select email,name,customer_id,role,salt,hash from users where email=?",
                      (email,))
        return rows[0] if rows else None

    # -- assets ----------------------------------------------------------
    def list_assets(self, customer_id: str) -> list[Site]:
        rows = self.q("select data from assets where customer_id=? order by site_id", (customer_id,))
        return [Site.model_validate_json(r["data"]) for r in rows]

    def get_asset(self, customer_id: str, site_id: str) -> Site | None:
        rows = self.q("select data from assets where customer_id=? and site_id=?",
                      (customer_id, site_id))
        return Site.model_validate_json(rows[0]["data"]) if rows else None

    def replace_assets(self, customer_id: str, sites: list[Site]) -> None:
        self.q("delete from assets where customer_id=?", (customer_id,))
        for s in sites:
            self.q("insert into assets(customer_id,site_id,data) values(?,?,?)",
                   (customer_id, s.site_id, s.model_dump_json()))

    # -- SOP rules -------------------------------------------------------
    def list_rules(self, customer_id: str) -> list[SopRule]:
        rows = self.q("select data from sop_rules where customer_id=?", (customer_id,))
        rules = [SopRule.model_validate_json(r["data"]) for r in rows]
        rules.sort(key=lambda r: (r.priority, r.rule_id))
        return rules

    def next_rule_id(self, customer_id: str) -> str:
        rows = self.q("select rule_id from sop_rules where customer_id=?", (customer_id,))
        nums = [int(r["rule_id"][2:]) for r in rows if r["rule_id"].startswith("R-")]
        return f"R-{(max(nums) + 1) if nums else 1:03d}"

    def upsert_rule(self, customer_id: str, rule: SopRule) -> None:
        self.q("insert into sop_rules(customer_id,rule_id,data) values(?,?,?) "
               "on conflict(customer_id,rule_id) do update set data=excluded.data",
               (customer_id, rule.rule_id, rule.model_dump_json()))

    def delete_rule(self, customer_id: str, rule_id: str) -> bool:
        existed = bool(self.q("select 1 as x from sop_rules where customer_id=? and rule_id=?",
                              (customer_id, rule_id)))
        self.q("delete from sop_rules where customer_id=? and rule_id=?", (customer_id, rule_id))
        return existed

    # -- acknowledgements ------------------------------------------------
    def add_ack(self, customer_id: str, alert_id: str, by: str, at: str) -> None:
        self.q("insert into acks(customer_id,alert_id,acked_by,acked_at) values(?,?,?,?) "
               "on conflict do nothing", (customer_id, alert_id, by, at))

    def get_ack(self, customer_id: str, alert_id: str) -> dict | None:
        rows = self.q("select acked_by,acked_at from acks where customer_id=? and alert_id=?",
                      (customer_id, alert_id))
        return rows[0] if rows else None

    def acks_map(self, customer_id: str) -> dict:
        rows = self.q("select alert_id,acked_by,acked_at from acks where customer_id=?",
                      (customer_id,))
        return {r["alert_id"]: (r["acked_by"], r["acked_at"]) for r in rows}

    # -- audit -----------------------------------------------------------
    def add_audit(self, customer_id: str, at: str, actor: str, action: str, details: str) -> None:
        self.q("insert into audit(customer_id,at,actor,action,details) values(?,?,?,?,?)",
               (customer_id, at, actor, action, details))

    def list_audit(self, customer_id: str, limit: int = 200) -> list[dict]:
        return self.q("select id,at,actor,action,details from audit where customer_id=? "
                      "order by id desc limit ?", (customer_id, limit))

    # -- advisor ---------------------------------------------------------
    def save_suggestion(self, customer_id: str, suggestion_id: str, incident_id: str,
                        data: str, created_at: str) -> None:
        self.q("insert into advisor_suggestions(customer_id,suggestion_id,incident_id,data,"
               "created_at) values(?,?,?,?,?) on conflict do nothing",
               (customer_id, suggestion_id, incident_id, data, created_at))

    def suggestions_for_incident(self, customer_id: str, incident_id: str) -> list[dict]:
        return self.q("select suggestion_id,incident_id,data,created_at from advisor_suggestions "
                      "where customer_id=? and incident_id=?", (customer_id, incident_id))

    def get_suggestion(self, customer_id: str, suggestion_id: str) -> dict | None:
        rows = self.q("select suggestion_id,incident_id,data,created_at from advisor_suggestions "
                      "where customer_id=? and suggestion_id=?", (customer_id, suggestion_id))
        return rows[0] if rows else None

    def add_decision(self, customer_id: str, suggestion_id: str, decision: str, note: str,
                     by: str, at: str) -> None:
        self.q("insert into advisor_decisions(customer_id,suggestion_id,decision,note,"
               "decided_by,decided_at) values(?,?,?,?,?,?) on conflict do nothing",
               (customer_id, suggestion_id, decision, note, by, at))

    def get_decision(self, customer_id: str, suggestion_id: str) -> dict | None:
        rows = self.q("select suggestion_id,decision,note,decided_by,decided_at from "
                      "advisor_decisions where customer_id=? and suggestion_id=?",
                      (customer_id, suggestion_id))
        return rows[0] if rows else None

    def list_decisions(self, customer_id: str) -> list[dict]:
        return self.q("select suggestion_id,decision,note,decided_by,decided_at from "
                      "advisor_decisions where customer_id=? order by decided_at desc",
                      (customer_id,))


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        # Neon on Vercel injects DATABASE_URL and/or POSTGRES_URL; ignore non-Postgres
        # values (e.g. a stray Prisma "file:./dev.db") and fall back to SQLite.
        url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        if url and not url.startswith(("postgres://", "postgresql://")):
            url = None
        _db =Database(url=url) if url else Database(sqlite_path=_sqlite_path())
    return _db


def configure(url: str | None = None, sqlite_path: str | None = None) -> Database:
    """Reset the singleton (used by tests and by DATABASE_URL switches)."""
    global _db
    _db = Database(url=url, sqlite_path=sqlite_path)
    return _db
