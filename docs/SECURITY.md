# Security

What this service defends against, how, and what it deliberately does not do. Every control
below has a test in `backend/tests/test_security.py` or `test_auth_tenancy.py` — if a claim
here has no test, it is marked as untested rather than asserted.

## Threat model

A public HTTPS API with bearer-token auth, no cookies, one Postgres database shared by
several tenants, and one paid LLM dependency. Ranked by what is actually likely:

| Risk | Control | Test |
|:--|:--|:--|
| Credential stuffing on `/auth/login` | 10 attempts/min per IP **and** 10 per 5 min per account | `test_login_is_rate_limited` |
| Account enumeration by response timing | Unknown accounts run the same 200k-round PBKDF2 as real ones | `test_unknown_account_costs_the_same_as_a_real_one` |
| Cost exhaustion on the paid advisor route | 15/min, a separate and much tighter class than reads | `test_advisor_has_a_tighter_limit_than_reads` |
| Forged tokens | HS256 pinned; `alg: none` rejected; `exp`/`sub`/`cid`/`role` all required | `test_token_pins_the_algorithm_and_requires_its_claims` |
| Signing with the published dev default | Missing `JWT_SECRET` is **fatal** in production | `test_production_refuses_a_missing_signing_secret` |
| Cross-tenant data access | Every query scoped by `customer_id` from the token | `test_tenant_isolation` |
| Partner roles reading company data | Company endpoints return 403 to partner roles | `test_partner_roles_cannot_read_company_data` |
| Information leakage in errors | One handler: logs the detail, returns a request id and nothing else | `test_unhandled_errors_return_an_id_and_nothing_else` |
| Rate-limit evasion via `x-forwarded-for` | Prefers `x-real-ip`; uses the **last** forwarded hop, never the client-supplied first | `test_forwarded_for_cannot_be_spoofed_to_dodge_the_limit` |
| Oversized request bodies | 1 MiB cap, refused with 413 before the body is read | `test_oversized_body_is_refused` |
| MIME sniffing, framing, referrer leakage | `nosniff`, `DENY`, `strict-origin-when-cross-origin`, `default-src 'none'` | `test_security_headers_on_every_response` |
| Tenant data cached by a shared proxy | `Cache-Control: no-store` on every response | `test_security_headers_on_every_response` |
| SQL injection | Every query parameterised; no string-built SQL anywhere in `app/` | audited, see below |

## Honest limitations

These are real gaps. They are listed because a reader deserves to know them, not buried.

- **The rate limiter is in-process.** On Vercel each function instance keeps its own counters,
  so the effective limit is (limit × live instances). It is a genuine speed bump against one
  attacker on one connection; it is **not** a distributed rate limit. Doing it properly needs
  Redis or Vercel's WAF. Nothing here claims otherwise.
- **No account lockout and no MFA.** Throttling slows credential stuffing; it does not stop a
  patient attacker with a good password list.
- **No token revocation.** Tokens carry `iat` and `jti` so a leaked one is identifiable in the
  audit log, but there is no deny-list: a stolen token is valid for its full 12 hours.
- **`JWT_SECRET` length is a warning, not an error.** A short real secret is weaker than it
  should be, but it is not forgeable the way the published default is, and taking a running
  deployment down over key length would be the larger outage. Rotate it to 32+ bytes.
- **CORS defaults to `*`** when `ALLOWED_ORIGINS` is unset, logging a warning in production.
  This is tolerable only because auth is a bearer token and there are no cookies, so a hostile
  page cannot ride a browser session. Production should still pin it.
- **No pen test.** Nothing here has been tested by anyone but us.
- **Dependencies are unpinned** in `requirements.txt`, so a build picks up whatever is current.
  Reproducible builds need a lockfile.

## Deliberate decisions that may look like holes

- **`GET /api/detections` is readable by partner roles.** This is intended. The rows are public
  NASA FIRMS satellite records — latitude, longitude, time, satellite, confidence, FRP — with
  no site, asset, personnel or ownership data in them, and the partner roles (fire service,
  government, NGO) exist precisely to see the fire situation. Every endpoint that *joins* a
  detection to a site requires a staff role. `window_hours` is capped at 48 so it cannot be
  used to pull the archive in one request. The test asserts both halves: partners get the
  detections, and a detection never carries a site or asset field.
- **Demo credentials are in the README.** They are demo-only accounts on simulated data. Any
  real deployment seeds its own.
- **Asset values never leave the owning company**, by sharing policy, even for the fire
  service. That is a product decision as much as a security one.

## Secrets

Handled as environment variables only; none are in the repository, and `.env*` is git-ignored.

| Variable | Purpose | Missing behaviour |
|:--|:--|:--|
| `JWT_SECRET` | Token signing | **Fatal in production**; dev default with a warning locally |
| `DATABASE_URL` | Postgres | Falls back to a local SQLite file |
| `GROQ_API_KEY` | AI advisor | Advisor falls back to the template engine |
| `WEATHERAPI_KEY` | Live weather | Live weather endpoint reports unavailable |
| `FIRMS_MAP_KEY` | Live fire detections | Live fire endpoint reports unavailable |
| `ALLOWED_ORIGINS` | CORS allow-list | `*`, with a warning logged in production |

Every third-party provider is written to **return nothing rather than raise**: a weather or
fire API outage must not take the risk score down with it. `docs/RELIABILITY.md` has the full
failure-mode table.

Licensed brand fonts are deliberately kept out of the repository (`.gitignore`), so a clone
builds without them and nobody redistributes a font they have no licence to.

## Auditing this yourself

```bash
cd backend
python -m pytest tests/test_security.py tests/test_auth_tenancy.py -v --import-mode=importlib

# no string-built SQL anywhere (expect no matches in app/):
grep -rnE 'execute\(f"|\.q\(f"' app/

# no secret committed (expect no matches):
git grep -nE 'gsk_|sk-[A-Za-z0-9]{20}|JWT_SECRET *= *["'"'"']'
```

## Reporting

This is a hackathon project, not a production service. If you find something, open an issue on
the repository — there is no bug bounty and no on-call rotation, and pretending otherwise would
be worse than saying so.
