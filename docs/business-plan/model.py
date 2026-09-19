"""model.py — PyraGrid five-year financial model (FY2026–FY2031).

Every number in PyraGrid_Business_Plan.md comes from this file, so the plan stays
internally consistent. Change an assumption, run `python build_plan.py`, and every table
in PyraGrid_Business_Plan.md is regenerated.

Competition rules built in: electricity costs 40 % more than the reference tariff, and
shipping is available only one day a week.
"""
from __future__ import annotations

import math

YEARS = [2026, 2027, 2028, 2029, 2030, 2031]
N = len(YEARS)

# ------------------------------------------------------------------ assumptions
A = dict(
    customers_end=[0, 6, 18, 40, 70, 110],          # paying customers at year end
    sites_per_customer=[0, 10, 14, 19, 23.5, 26],   # average monitored sites per customer
    pro_mix=[0, 0.40, 0.50, 0.55, 0.60, 0.62],      # share of sites on Professional
    price_essential=1800.0,                          # € per site per year (2026 list)
    price_pro=3600.0,
    price_uplift=[0, 0, 0, 0.03, 0.03, 0.03],        # annual list-price increase
    sensor_attach=[0, 0.15, 0.20, 0.25, 0.30, 0.35], # share of sites with the sensor network
    sensor_fee=2400.0,                               # Sensor-as-a-Service, € per site per year
    pilot_sensor_sites=3,                            # 2026 grant-funded pilots (no revenue)
    onboarding_fee=2000.0,                           # € per new customer
    training_fee=1000.0,                             # drills and training, € per customer per year
    logo_churn=0.08,                                 # annual customer churn from 2028
    # cost of revenue
    cloud_per_site=70.0, llm_per_site=15.0,          # € per site per year
    support_pct=0.08,                                # customer success in cost of revenue
    sensors_per_site=30, sensor_unit_cost=85.0, gateway_cost=450.0,
    install_cost=1200.0,                             # field install, expensed
    sensor_opex=250.0,                               # connectivity, batteries, visits per site per year
    sensor_life=4, sensor_replacement=0.10,
    # competition rule 1: electricity costs 40 % more than the reference tariff
    elec_price=0.20,                                 # € per kWh, reference business tariff
    elec_surcharge=0.40,                             # +40 %
    dc_energy_share=0.30,                            # share of cloud and AI cost that is data-centre electricity
    gateway_kwh=150,                                 # kWh per sensor site per year (gateway, charging, testing)
    office_kwh_per_fte=2500,                         # kWh per employee per year (office and sensor workshop)
    # competition rule 2: shipping only one day a week
    stock_weeks=6,                                   # weeks of sensor kits kept in stock (1-week cycle + transit + safety)
    spare_sensors_per_site=2,                        # spares left on each sensor site, since a part cannot be sent next day
    freight_pct=0.04,                                # weekly consolidated freight, % of hardware bought
    # operating expenses (fully loaded annual cost per FTE, 2026 €, +3 %/yr)
    founders=2, founder_pay=[30000, 36000, 55000, 70000, 80000, 90000],
    fte_eng=[0, 2, 4, 6, 9, 12], cost_eng=58000,
    fte_sales=[0, 1, 2, 4, 6, 8], cost_sales=62000,
    fte_cs=[0, 1, 2, 4, 6, 8], cost_cs=45000,
    fte_ga=[0, 0.5, 1, 2, 3, 4], cost_ga=50000,
    wage_growth=0.03,
    marketing_fixed=[5000, 30000, 60000, 120000, 180000, 250000],
    marketing_pct=0.10,
    other_opex=[10000, 45000, 90000, 160000, 230000, 300000],
    # funding and tax
    founders_equity=10000, preseed=300000, seed=1500000, series_a=0,
    enisa_loan=150000, enisa_rate=0.04, grant=[0, 150000, 100000, 0, 0, 0],
    tax_new=0.15, tax_std=0.25,
    dso_days=45, dpo_days=30, deferred_share=0.45,
    wacc=0.25, g_terminal=0.03, arr_multiple=6.0,
)


def run(a: dict = A, price_factor: float = 1.0, growth_factor: float = 1.0, churn: float | None = None):
    churn = a["logo_churn"] if churn is None else churn
    r: dict[str, list[float]] = {k: [0.0] * N for k in [
        "customers", "new_customers", "sites", "avg_sites", "price_es", "price_pro", "blended",
        "sensor_sites", "avg_sensor_sites", "new_sensor_sites", "rev_platform", "rev_sensor",
        "rev_services", "revenue", "cogs_cloud", "cogs_energy", "cogs_freight", "opex_energy",
        "elec_extra", "inventory", "cogs_support", "cogs_sensor_ops", "cogs_install",
        "depreciation", "cogs", "gross", "opex_people", "opex_marketing", "opex_other", "opex",
        "ebitda", "ebit", "interest", "grant", "ebt", "tax", "net", "capex", "fleet_gross",
        "fleet_net", "arr", "ar", "ap", "deferred", "nwc", "cfo", "cff", "cash", "loan",
        "equity_in", "paid_in", "retained", "assets", "liab_eq", "fte", "sm_cost", "fcf"]}
    fleet_adds: list[float] = []            # capex vintages for straight-line depreciation
    carry = 0.0                             # tax losses carried forward
    profitable_years = 0
    price_mult = 1.0
    prev_sites = prev_sensor = 0.0
    for i, y in enumerate(YEARS):
        # --- customers and sites
        cust = round(a["customers_end"][i] * growth_factor)
        if i >= 2:                                           # churn replaced by extra sales
            cust = max(cust, 0)
        prev_c = r["customers"][i - 1] if i else 0
        lost = round(prev_c * churn) if i >= 2 else 0
        r["customers"][i] = cust
        r["new_customers"][i] = max(0, cust - prev_c + lost)
        sites = cust * a["sites_per_customer"][i]
        r["sites"][i] = sites
        r["avg_sites"][i] = (prev_sites + sites) / 2
        # --- prices
        price_mult *= 1 + a["price_uplift"][i]
        pe, pp = a["price_essential"] * price_mult * price_factor, a["price_pro"] * price_mult * price_factor
        r["price_es"][i], r["price_pro"][i] = pe, pp
        mix = a["pro_mix"][i]
        r["blended"][i] = pe * (1 - mix) + pp * mix
        # --- sensors
        s_sites = sites * a["sensor_attach"][i] + (a["pilot_sensor_sites"] if i == 0 else 0)
        s_sites = max(s_sites, prev_sensor)
        r["sensor_sites"][i] = s_sites
        r["avg_sensor_sites"][i] = (prev_sensor + s_sites) / 2
        new_s = s_sites - prev_sensor
        r["new_sensor_sites"][i] = new_s
        # --- revenue (the 2026 pilots are free)
        r["rev_platform"][i] = r["avg_sites"][i] * r["blended"][i]
        paying_sensor = max(0.0, r["avg_sensor_sites"][i] - (a["pilot_sensor_sites"] if i <= 1 else 0))
        r["rev_sensor"][i] = paying_sensor * a["sensor_fee"] * price_factor
        r["rev_services"][i] = r["new_customers"][i] * a["onboarding_fee"] + (cust * a["training_fee"] if i >= 2 else 0)
        rev = r["rev_platform"][i] + r["rev_sensor"][i] + r["rev_services"][i]
        r["revenue"][i] = rev
        # --- capex and depreciation (sensor fleet)
        kit = a["sensors_per_site"] * a["sensor_unit_cost"] + a["gateway_cost"]
        capex = new_s * kit + prev_sensor * a["sensor_replacement"] * a["sensors_per_site"] * a["sensor_unit_cost"]
        r["capex"][i] = capex
        fleet_adds.append(capex)
        dep = 0.0
        for j, c in enumerate(fleet_adds):             # half-year convention
            age = i - j
            if age == 0:
                dep += c / a["sensor_life"] / 2
            elif age < a["sensor_life"]:
                dep += c / a["sensor_life"]
            elif age == a["sensor_life"]:
                dep += c / a["sensor_life"] / 2
        r["depreciation"][i] = dep
        # --- cost of revenue
        ef = 1 + a["elec_surcharge"]
        cloud_all = r["avg_sites"][i] * (a["cloud_per_site"] + a["llm_per_site"]) + (2000 if i == 0 else 0)
        dc_energy = cloud_all * a["dc_energy_share"]                    # at the reference tariff
        site_energy = r["avg_sensor_sites"][i] * a["gateway_kwh"] * a["elec_price"]
        r["cogs_cloud"][i] = cloud_all - dc_energy
        r["cogs_energy"][i] = (dc_energy + site_energy) * ef
        r["cogs_freight"][i] = a["freight_pct"] * capex
        r["cogs_support"][i] = a["support_pct"] * (r["rev_platform"][i] + r["rev_sensor"][i])
        r["cogs_sensor_ops"][i] = r["avg_sensor_sites"][i] * a["sensor_opex"]
        r["cogs_install"][i] = new_s * a["install_cost"]
        cogs = r["cogs_cloud"][i] + r["cogs_energy"][i] + r["cogs_freight"][i] + r["cogs_support"][i] + r["cogs_sensor_ops"][i] + r["cogs_install"][i] + dep
        r["cogs"][i] = cogs
        r["gross"][i] = rev - cogs
        # --- operating expenses
        w = (1 + a["wage_growth"]) ** i
        people = (a["founders"] * a["founder_pay"][i]
                  + (a["fte_eng"][i] * a["cost_eng"] + a["fte_sales"][i] * a["cost_sales"]
                     + a["fte_cs"][i] * a["cost_cs"] + a["fte_ga"][i] * a["cost_ga"]) * w)
        r["opex_people"][i] = people
        r["opex_marketing"][i] = a["marketing_fixed"][i] + a["marketing_pct"] * rev
        r["opex_other"][i] = a["other_opex"][i]
        r["fte"][i] = a["founders"] + a["fte_eng"][i] + a["fte_sales"][i] + a["fte_cs"][i] + a["fte_ga"][i]
        office_energy = r["fte"][i] * a["office_kwh_per_fte"] * a["elec_price"]
        r["opex_energy"][i] = office_energy * ef
        r["elec_extra"][i] = (dc_energy + site_energy + office_energy) * a["elec_surcharge"]
        r["opex"][i] = people + r["opex_marketing"][i] + r["opex_other"][i] + r["opex_energy"][i]
        r["sm_cost"][i] = a["fte_sales"][i] * a["cost_sales"] * w + r["opex_marketing"][i]
        r["ebitda"][i] = r["gross"][i] + dep - r["opex"][i]          # EBITDA adds back depreciation
        r["ebit"][i] = r["ebitda"][i] - dep
        # --- financing items
        loan_prev = r["loan"][i - 1] if i else 0.0
        loan = a["enisa_loan"] if i in (0, 1, 2) else max(0.0, loan_prev - a["enisa_loan"] / 3)
        r["loan"][i] = loan
        r["interest"][i] = a["enisa_rate"] * (loan_prev + loan) / 2 if i else a["enisa_rate"] * loan / 2
        r["grant"][i] = a["grant"][i]
        ebt = r["ebit"][i] - r["interest"][i] + r["grant"][i]
        r["ebt"][i] = ebt
        # --- tax with loss carry-forward and the 15 % rate for the first two profitable years
        if ebt <= 0:
            carry += -ebt
            tax = 0.0
        else:
            used = min(carry, ebt)
            carry -= used
            base = ebt - used
            rate = a["tax_new"] if profitable_years < 2 else a["tax_std"]
            tax = base * rate
            if base > 0:
                profitable_years += 1
        r["tax"][i] = tax
        r["net"][i] = ebt - tax
        # --- working capital
        r["arr"][i] = sites * r["blended"][i] + max(0.0, s_sites - (a["pilot_sensor_sites"] if i <= 1 else 0)) * a["sensor_fee"] * price_factor
        r["ar"][i] = rev * a["dso_days"] / 365
        r["ap"][i] = (r["cogs"][i] - dep + r["opex_marketing"][i] + r["opex_other"][i]) * a["dpo_days"] / 365
        r["deferred"][i] = a["deferred_share"] * (r["rev_platform"][i] + r["rev_sensor"][i]) * (sites / r["avg_sites"][i] if r["avg_sites"][i] else 0) if i else 0
        # weekly shipping: kits held in stock plus spare sensors left on every sensor site
        r["inventory"][i] = capex * a["stock_weeks"] / 52 + s_sites * a["spare_sensors_per_site"] * a["sensor_unit_cost"]
        r["nwc"][i] = r["ar"][i] + r["inventory"][i] - r["ap"][i] - r["deferred"][i]
        d_nwc = r["nwc"][i] - (r["nwc"][i - 1] if i else 0.0)
        r["cfo"][i] = r["net"][i] + dep - d_nwc
        # --- equity rounds
        equity = {0: a["founders_equity"] + a["preseed"], 2: a["seed"], 3: a["series_a"]}.get(i, 0.0)
        r["equity_in"][i] = equity
        r["cff"][i] = equity + (loan - loan_prev if i else loan)
        r["cash"][i] = (r["cash"][i - 1] if i else 0.0) + r["cfo"][i] - capex + r["cff"][i]
        r["fcf"][i] = r["cfo"][i] - capex
        # --- balance sheet
        r["fleet_gross"][i] = sum(fleet_adds)
        r["fleet_net"][i] = (r["fleet_net"][i - 1] if i else 0.0) + capex - dep
        r["paid_in"][i] = (r["paid_in"][i - 1] if i else 0.0) + equity
        r["retained"][i] = (r["retained"][i - 1] if i else 0.0) + r["net"][i]
        r["assets"][i] = r["cash"][i] + r["ar"][i] + r["inventory"][i] + r["fleet_net"][i]
        r["liab_eq"][i] = r["ap"][i] + r["deferred"][i] + loan + r["paid_in"][i] + r["retained"][i]
        prev_sites, prev_sensor = sites, s_sites
    return r


def valuation(r: dict, a: dict = A):
    """DCF of FY2027–31 free cash flow with a Gordon terminal value, and an ARR-multiple exit."""
    pv = 0.0
    for i in range(1, N):
        pv += r["fcf"][i] / (1 + a["wacc"]) ** i
    tv = r["fcf"][-1] * (1 + a["g_terminal"]) / (a["wacc"] - a["g_terminal"])
    pv_tv = tv / (1 + a["wacc"]) ** (N - 1)
    exit_val = r["arr"][-1] * a["arr_multiple"]
    return pv, tv, pv_tv, pv + pv_tv, exit_val, exit_val / (1 + a["wacc"]) ** (N - 1)


def irr(flows: list[float]) -> float:
    lo, hi = -0.99, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        npv = sum(f / (1 + mid) ** t for t, f in enumerate(flows))
        lo, hi = (mid, hi) if npv > 0 else (lo, mid)
    return (lo + hi) / 2


if __name__ == "__main__":
    r = run()
    for k in ["customers", "sites", "sensor_sites", "revenue", "gross", "ebitda", "net", "cash", "arr", "fte"]:
        print(f"{k:14s}", " ".join(f"{v:>12,.0f}" for v in r[k]))
    print("balance check  ", " ".join(f"{a - b:>12,.0f}" for a, b in zip(r["assets"], r["liab_eq"])))
    print("valuation", [round(x) for x in valuation(r)])
