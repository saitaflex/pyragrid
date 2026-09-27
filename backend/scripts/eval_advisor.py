"""eval_advisor.py — measured evaluation of the AI Advisor.

Answers, with numbers instead of claims: does the model stay grounded in the evidence
we give it, do the safety guardrails actually catch anything, how long does a call take
and what does it cost. Runs the same cases through every configured engine so Groq,
Ollama and the no-AI template engine can be compared side by side.

    cd backend
    GROQ_API_KEY=... python scripts/eval_advisor.py            # Groq + template
    OLLAMA_URL=http://localhost:11434 python scripts/eval_advisor.py   # local open model
    python scripts/eval_advisor.py --cases 12 --json out.json

With no key set it still reports the template engine, so the deterministic path has
measured numbers too. Cases come from the real FIRMS replay, not from fixtures.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import advisor, config, state  # noqa: E402
from app.defaults import default_rules  # noqa: E402
from app.importer import seed_sites  # noqa: E402
from app.providers.llm import GroqProvider, OllamaProvider  # noqa: E402
from app import sensors  # noqa: E402
from app.defaults import DEMO_SENSOR_SITES  # noqa: E402

# Groq list price for openai/gpt-oss-120b, USD per million tokens. Verify at
# https://groq.com/pricing before quoting; token counts below are measured, cost is derived.
USD_IN_PER_M = 0.15
USD_OUT_PER_M = 0.75


def build_cases(limit: int) -> list[dict]:
    """Real incidents from the FIRMS replay: the worst step of each escalating site."""
    rd = state.get_replay("demo")
    rules = default_rules()
    rank = {"NORMAL": 0, "ELEVATED": 1, "HIGH": 2, "CRITICAL": 3}
    cases = []
    for sid, statuses in rd.statuses.items():
        best = max(range(len(statuses)), key=lambda i: rank[statuses[i].level])
        if rank[statuses[best].level] < 2:      # only HIGH and CRITICAL are worth advising on
            continue
        cases.append({"site_id": sid, "step": best, "at": rd.steps[best],
                      "level": statuses[best].level,
                      "site": rd.sites[sid], "status": statuses[best],
                      "headline": rd.headlines[sid][best], "rules": rules})
    cases.sort(key=lambda c: (-rank[c["level"]], c["site_id"]))
    return cases[:limit]


def ground_for(case: dict, rd):
    """Sensor mesh when the site has one, so the sensor evidence keys are exercised too."""
    sid = case["site_id"]
    if sid not in DEMO_SENSOR_SITES:
        return None
    installs = {s: "2025-07-01T00:00:00Z" for s in DEMO_SENSOR_SITES}
    meshes, nodes, _ = sensors.snapshot(rd.sites, installs, case["at"],
                                        site_id=sid, event_limit=0)
    return (meshes[0], nodes) if meshes else None


def reject_reasons(raw: list[dict], allowed: list[str]) -> dict[str, int]:
    """Why each suggestion would be dropped — the guardrail breakdown app code doesn't keep."""
    keys = set(allowed)
    out: dict[str, int] = {}

    def bump(k: str) -> None:
        out[k] = out.get(k, 0) + 1

    for item in raw[:10]:
        if not isinstance(item, dict):
            bump("not_an_object")
            continue
        missing = [f for f in ("title", "detail", "audience", "priority", "evidence")
                   if f not in item]
        if missing:
            bump("missing_fields")
            continue
        title, detail = str(item["title"]).strip(), str(item["detail"]).strip()
        if advisor.TACTICS.search(f"{title} {detail}"):
            bump("firefighting_tactics")       # the safety-critical one
        if not (0 < len(title) <= 120) or not (0 < len(detail) <= 600):
            bump("length")
        if item["audience"] not in advisor._AUDIENCES:
            bump("bad_audience")
        if item["priority"] not in (1, 2, 3):
            bump("bad_priority")
        ev = item["evidence"]
        if not isinstance(ev, list) or not ev:
            bump("no_evidence")
        elif any(k not in keys for k in ev):
            bump("hallucinated_evidence_key")  # cited something we never gave it
    return out


def run_engine(name: str, provider, cases: list[dict], rd) -> dict:
    lat, n_ok, n_fail = [], 0, 0
    raw_sugs = cited = grounded = 0
    reasons: dict[str, int] = {}
    tok_in = tok_out = 0
    errors: list[str] = []

    for case in cases:
        ground = ground_for(case, rd)
        rule_ids = advisor.matched_rule_ids(case["status"], case["site"], case["rules"])
        keys = advisor.evidence_keys(case["site"], case["status"], rule_ids, ground)
        context = advisor.build_context(case["site"], case["status"], case["headline"],
                                        case["rules"], ground)
        msg = f"EVIDENCE_KEYS: {json.dumps(keys)}\nCONTEXT: {json.dumps(context)}"

        t0 = time.perf_counter()
        try:
            if provider is None:
                raw = advisor.template_engine(case["site"], case["status"], rule_ids, ground)
            else:
                raw = provider.suggest(advisor.SYSTEM_PROMPT, msg)
        except Exception as e:  # noqa: BLE001
            n_fail += 1
            errors.append(f"{case['site_id']}: {str(e)[:90]}")
            continue
        lat.append(time.perf_counter() - t0)

        if provider is not None and getattr(provider, "last_usage", None):
            tok_in += provider.last_usage.get("prompt_tokens", 0) or 0
            tok_out += provider.last_usage.get("completion_tokens", 0) or 0

        raw_sugs += len(raw)
        for item in raw:
            ev = item.get("evidence") if isinstance(item, dict) else None
            if isinstance(ev, list) and ev:
                cited += len(ev)
                grounded += sum(1 for k in ev if k in set(keys))
        for k, v in reject_reasons(raw, keys).items():
            reasons[k] = reasons.get(k, 0) + v
        valid, _ = advisor.validate(raw, keys)
        n_ok += 1 if valid else 0

    out = {
        "engine": name,
        "model": getattr(provider, "model", None),
        "cases": len(cases),
        "usable_answers": n_ok,
        "call_failures": n_fail,
        "raw_suggestions": raw_sugs,
        "suggestions_surviving_guardrails": None,
        "evidence_citations": cited,
        "grounded_citations": grounded,
        "grounding_pct": round(100.0 * grounded / cited, 1) if cited else None,
        "guardrail_rejections": reasons,
        "latency_s": {
            "p50": round(statistics.median(lat), 2) if lat else None,
            "p95": round(sorted(lat)[max(0, int(0.95 * len(lat)) - 1)], 2) if lat else None,
            "max": round(max(lat), 2) if lat else None,
        },
        "tokens": {"in": tok_in, "out": tok_out} if tok_in or tok_out else None,
        "errors": errors[:5],
    }
    if tok_in or tok_out:
        per_call = (tok_in / 1e6 * USD_IN_PER_M + tok_out / 1e6 * USD_OUT_PER_M) / max(1, len(lat))
        out["usd_per_call"] = round(per_call, 5)
        out["usd_per_1000_calls"] = round(per_call * 1000, 2)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=10)
    ap.add_argument("--json", type=str, default="")
    ap.add_argument("--timeout", type=float, default=0.0,
                    help="override the product's LLM timeout for measurement only: a slow "
                         "local model still gets measured instead of only timing out")
    args = ap.parse_args()

    product_timeout = config.LLM_TIMEOUT_S
    if args.timeout:
        config.LLM_TIMEOUT_S = args.timeout
        print(f"measuring with a {args.timeout:.0f}s timeout; the product itself falls "
              f"back to the template engine after {product_timeout}s\n")

    cases = build_cases(args.cases)
    print(f"{len(cases)} real incidents from the FIRMS replay "
          f"({sum(1 for c in cases if c['level'] == 'CRITICAL')} CRITICAL, "
          f"{sum(1 for c in cases if c['level'] == 'HIGH')} HIGH)\n")

    engines: list[tuple[str, object]] = []
    if os.environ.get("GROQ_API_KEY"):
        engines.append(("groq", GroqProvider()))
    if os.environ.get("OLLAMA_URL"):
        engines.append(("ollama", OllamaProvider()))
    engines.append(("template (no AI)", None))

    rd = state.get_replay("demo")
    results = [run_engine(name, prov, cases, rd) for name, prov in engines]

    for r in results:
        print(f"--- {r['engine']}" + (f"  [{r['model']}]" if r["model"] else ""))
        print(f"    usable answers      {r['usable_answers']}/{r['cases']}"
              f"   call failures {r['call_failures']}")
        print(f"    evidence grounding  {r['grounding_pct']}%"
              f"  ({r['grounded_citations']}/{r['evidence_citations']} citations were keys we gave it)")
        print(f"    guardrails caught   {r['guardrail_rejections'] or 'nothing'}")
        lt = r["latency_s"]
        print(f"    latency             p50 {lt['p50']}s  p95 {lt['p95']}s  max {lt['max']}s")
        if r.get("tokens"):
            print(f"    tokens              {r['tokens']['in']} in / {r['tokens']['out']} out"
                  f"   ≈ ${r['usd_per_call']}/call, ${r['usd_per_1000_calls']}/1000 calls")
        for e in r["errors"]:
            print(f"    error               {e}")
        print()

    if not os.environ.get("GROQ_API_KEY") and not os.environ.get("OLLAMA_URL"):
        print("No GROQ_API_KEY or OLLAMA_URL set: only the template engine was measured.")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"cases": [{k: c[k] for k in ("site_id", "at", "level")} for c in cases],
             "results": results,
             "timeout_s": config.LLM_TIMEOUT_S,
             "max_suggestions": config.MAX_SUGGESTIONS},
            indent=1), encoding="utf-8")
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
