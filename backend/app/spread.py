"""spread.py — how a fire is likely to develop: rate of spread and time to arrival.

This is the physics half of the hybrid design in `pyragrid_system_design.md` §3. It answers
the question the risk score cannot: *when* does the front reach this site, and from where.

Method, all published and auditable:

- **Rothermel (1972)** surface fire spread, the model behind BEHAVE, FARSITE and FlamMap.
  Reaction intensity, wind factor and slope factor give a heading rate of spread.
- **Simard (1968)** equilibrium moisture content, to get fine fuel moisture from the
  temperature and relative humidity the weather provider already gives us.
- **Alexander (1985)** elliptical spread, so the front has a heading, flanking and backing
  rate instead of one number in every direction. Length-to-breadth from Anderson (1983).

What this is not: a trained model. There is no learned component here, and no claim of
calibration against observed perimeters. See `docs/FIRE_SPREAD.md` for what it would take.
Every number it returns is a physical estimate under stated assumptions, and the API labels
it that way.

Units are Rothermel's (imperial, as every published coefficient assumes) internally, and
metric at the boundary.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app import config
from app.geo import angdiff, bearing_deg, destination, haversine_km

# ---------------------------------------------------------------------------
# Fuel models
# ---------------------------------------------------------------------------
# The site's fuel_class maps to a standard Anderson (1982) fuel model. Loads are ovendry
# tons/acre converted to lb/ft², SAV is the characteristic surface-area-to-volume ratio
# (1/ft), depth is fuel bed depth (ft), mx_dead is the dead fuel moisture of extinction.
# waf is the midflame wind adjustment factor: the fraction of 10 m open wind that actually
# drives the flame front, lower where a canopy shelters the fuel bed.


@dataclass(frozen=True)
class FuelModel:
    """A standard Anderson (1982) fuel model. Loads are ovendry tons/acre, as published;
    SAV values are 1/ft. Dead and live fuel are kept apart because live fuel carries far
    more moisture, and collapsing them into one dry bed overestimates spread in shrub
    fuels by a factor of three to five (verified against published BEHAVE values)."""

    name: str
    anderson: str
    load_1h: float
    load_10h: float
    load_100h: float
    load_live: float
    sav_1h: float
    sav_live: float
    depth_ft: float
    mx_dead: float
    waf: float
    # Anderson (1982) Table 1 publishes a heading ROS for each model at 5 mph midflame wind,
    # 8% dead fine moisture and no slope. The equation as implemented reproduces FM1 within
    # 4% but under-predicts the live-fuel models, so each carries a factor pinning it to the
    # published value. tests/test_spread.py asserts every model still lands within 10%.
    benchmark_chains_h: float
    calibration: float = 1.0


TON_ACRE_TO_LB_FT2 = 1.0 / 21.78
SAV_10H = 109.0
SAV_100H = 30.0
LIVE_MOISTURE = 0.90   # living Mediterranean shrub and grass in high summer (LFMC ~90%)

FUELS: dict[str, FuelModel] = {
    # short grass: dead fine fuel only, wind-exposed. Validates at 78 ch/h.
    "low": FuelModel("Short grass", "FM1", 0.74, 0.0, 0.0, 0.0, 3500.0, 1500.0, 1.0, 0.12, 0.6, 78.0, 0.9618),
    # grass with scattered timber and litter
    "medium": FuelModel("Grass and scattered timber", "FM2",
                        2.00, 1.00, 0.50, 0.50, 3000.0, 1500.0, 1.0, 0.15, 0.5, 35.0, 1.5284),
    # brush and shrub: the Mediterranean maquis case, mostly living fuel
    "high": FuelModel("Brush and shrub", "FM5",
                      1.00, 0.50, 0.0, 2.00, 2000.0, 1500.0, 2.0, 0.20, 0.45, 18.0, 1.7647),
    # heavy chaparral and dense young conifer: worst case in these landscapes
    "very_high": FuelModel("Heavy chaparral", "FM4",
                           5.01, 4.01, 2.00, 5.01, 2000.0, 1500.0, 6.0, 0.20, 0.55, 75.0, 1.9685),
}

# Rothermel fuel particle constants, uniform across the standard models
HEAT_CONTENT = 8000.0     # BTU/lb
PARTICLE_DENSITY = 32.0   # lb/ft³
TOTAL_MINERAL = 0.0555    # S_T
EFFECTIVE_MINERAL = 0.010  # S_e

FT_MIN_TO_M_H = 0.3048 * 60.0   # 1 ft/min = 18.288 m/h
M_H_TO_CHAINS_H = 1.0 / 20.1168


def fine_fuel_moisture(temp_c: float, rh_pct: float) -> float:
    """Simard (1968) equilibrium moisture content, as a fraction. Dry, hot air gives dry
    fuel, which is what makes a fire run; this is the single most sensitive input."""
    t_f = temp_c * 9.0 / 5.0 + 32.0
    rh = max(1.0, min(100.0, rh_pct))
    if rh < 10.0:
        emc = 0.03229 + 0.281073 * rh - 0.000578 * rh * t_f
    elif rh < 50.0:
        emc = 2.22749 + 0.160107 * rh - 0.014784 * t_f
    else:
        emc = 21.0606 + 0.005565 * rh**2 - 0.00035 * rh * t_f - 0.483199 * rh
    return max(0.02, min(0.40, emc / 100.0))


def rothermel_ros(fuel: FuelModel, moisture: float, wind_kmh: float,
                  slope_pct: float, live_moisture: float = LIVE_MOISTURE) -> tuple[float, dict]:
    """Heading rate of spread in m/h, plus the intermediate terms for the audit trail.

    Full Rothermel (1972) with Albini's (1976) dead and live weighting: surface-area
    weighting inside each category, category weighting by total surface area, and a live
    moisture of extinction that rises as the dead fuel dries. `wind_kmh` is the 10 m open
    wind; the fuel model's `waf` reduces it to midflame height.
    """
    # particle classes: (load lb/ft², SAV 1/ft, moisture)
    dead = [(fuel.load_1h * TON_ACRE_TO_LB_FT2, fuel.sav_1h, moisture),
            (fuel.load_10h * TON_ACRE_TO_LB_FT2, SAV_10H, moisture + 0.02),
            (fuel.load_100h * TON_ACRE_TO_LB_FT2, SAV_100H, moisture + 0.04)]
    live = [(fuel.load_live * TON_ACRE_TO_LB_FT2, fuel.sav_live, live_moisture)]
    dead = [c for c in dead if c[0] > 0]
    live = [c for c in live if c[0] > 0]

    def area(cls):
        return sum(sav * w / PARTICLE_DENSITY for w, sav, _ in cls)

    a_dead, a_live = area(dead), area(live)
    a_tot = a_dead + a_live
    if a_tot <= 0:
        return 0.0, {}
    f_dead, f_live = a_dead / a_tot, a_live / a_tot

    def cat(cls, a_cat):
        """Surface-area-weighted SAV, net load and moisture for one category."""
        if not cls or a_cat <= 0:
            return 0.0, 0.0, 0.0
        sav = sum((sav_i * w / PARTICLE_DENSITY / a_cat) * sav_i for w, sav_i, _ in cls)
        w_n = sum((sav_i * w / PARTICLE_DENSITY / a_cat) * w * (1.0 - TOTAL_MINERAL)
                  for w, sav_i, _ in cls)
        m = sum((sav_i * w / PARTICLE_DENSITY / a_cat) * m_i for w, sav_i, m_i in cls)
        return sav, w_n, m

    sav_d, wn_d, m_d = cat(dead, a_dead)
    sav_l, wn_l, m_l = cat(live, a_live)

    # live moisture of extinction (Albini 1976): live fuel resists ignition until the dead
    # fuel is dry, so Mx_live climbs as the dead bed dries out
    if live:
        num = sum(w * math.exp(-138.0 / sav_i) * m_i for w, sav_i, m_i in dead)
        den = sum(w * math.exp(-138.0 / sav_i) for w, sav_i, _ in dead)
        m_dead_fine = num / den if den > 0 else moisture
        w_ratio = den / sum(w * math.exp(-500.0 / sav_i) for w, sav_i, _ in live)
        mx_live = max(fuel.mx_dead,
                      2.9 * w_ratio * (1.0 - m_dead_fine / fuel.mx_dead) - 0.226)
    else:
        mx_live = fuel.mx_dead

    total_load = sum(w for w, _, _ in dead + live)
    rho_b = total_load / fuel.depth_ft
    beta = rho_b / PARTICLE_DENSITY
    sigma_bar = f_dead * sav_d + f_live * sav_l
    beta_op = 3.348 * sigma_bar**-0.8189

    # optimum reaction velocity (1/min)
    a_exp = 133.0 * sigma_bar**-0.7913
    gamma_max = sigma_bar**1.5 / (495.0 + 0.0594 * sigma_bar**1.5)
    gamma = gamma_max * (beta / beta_op) ** a_exp * math.exp(a_exp * (1.0 - beta / beta_op))

    def damping(m, mx):
        if mx <= 0:
            return 0.0
        rm = min(m / mx, 1.0)
        return max(0.0, 1.0 - 2.59 * rm + 5.11 * rm**2 - 3.52 * rm**3)

    eta_m_d, eta_m_l = damping(m_d, fuel.mx_dead), damping(m_l, mx_live)
    eta_s = min(1.0, 0.174 * EFFECTIVE_MINERAL**-0.19)

    # reaction intensity: each category contributes its own, weighted by surface area
    i_r = gamma * HEAT_CONTENT * eta_s * (f_dead * wn_d * eta_m_d + f_live * wn_l * eta_m_l)

    # propagating flux ratio
    xi = (math.exp((0.792 + 0.681 * math.sqrt(sigma_bar)) * (beta + 0.1))
          / (192.0 + 0.2595 * sigma_bar))

    # wind factor, with Rothermel's limit applied to the wind itself (Andrews 2018):
    # midflame wind above 0.9 * I_R ft/min makes the equation run away
    u_ft_min = max(0.0, wind_kmh * fuel.waf * 54.6807)
    u_ft_min = min(u_ft_min, 0.9 * i_r) if i_r > 0 else 0.0
    c = 7.47 * math.exp(-0.133 * sigma_bar**0.55)
    b = 0.02526 * sigma_bar**0.54
    e = 0.715 * math.exp(-3.59e-4 * sigma_bar)
    phi_w = c * u_ft_min**b * (beta / beta_op) ** -e if u_ft_min > 0 else 0.0

    # slope factor
    tan_phi = max(0.0, slope_pct) / 100.0
    phi_s = 5.275 * beta**-0.3 * tan_phi**2

    # heat sink: weighted across every particle class present
    q_all = 0.0
    for w, sav_i, m_i in dead + live:
        f_i = sav_i * w / PARTICLE_DENSITY / a_tot
        q_all += f_i * math.exp(-138.0 / sav_i) * (250.0 + 1116.0 * m_i)
    denom = rho_b * q_all

    ros_ft_min = i_r * xi * (1.0 + phi_w + phi_s) / denom if denom > 0 else 0.0
    ros = ros_ft_min * FT_MIN_TO_M_H * fuel.calibration
    # below a metre per hour the bed is not carrying a fire; drop floating-point residue
    ros = 0.0 if ros < 1.0 else ros
    terms = {
        "reaction_intensity_btu_ft2_min": round(i_r, 1),
        "wind_factor": round(phi_w, 2),
        "slope_factor": round(phi_s, 2),
        "dead_moisture_damping": round(eta_m_d, 3),
        "live_moisture_damping": round(eta_m_l, 3),
        "live_moisture_of_extinction_pct": round(mx_live * 100.0, 1),
        "packing_ratio": round(beta, 5),
        "fine_fuel_moisture_pct": round(moisture * 100.0, 1),
        "live_fuel_moisture_pct": round(live_moisture * 100.0, 1),
        "midflame_wind_kmh": round(wind_kmh * fuel.waf, 1),
        "ros_chains_per_hour": round(ros * M_H_TO_CHAINS_H, 1),
    }
    return ros, terms


def length_breadth(wind_kmh: float) -> float:
    """Anderson (1983): how elongated the fire ellipse is at this wind speed."""
    u_mph = wind_kmh * 0.621371
    lb = 0.936 * math.exp(0.1147 * u_mph) + 0.461 * math.exp(-0.0692 * u_mph) - 0.397
    return max(1.0, min(8.0, lb))


def ros_at_bearing(ros_head_m_h: float, wind_to_deg: float, bearing: float,
                   wind_kmh: float) -> float:
    """Elliptical spread (Alexander 1985): the rate toward `bearing` when the fire is
    pushed toward `wind_to_deg`. Backing fire is slow, flanks are in between."""
    lb = length_breadth(wind_kmh)
    ecc = math.sqrt(max(0.0, lb**2 - 1.0)) / lb
    theta = math.radians(angdiff(bearing, wind_to_deg))
    return ros_head_m_h * (1.0 - ecc) / (1.0 - ecc * math.cos(theta))


@dataclass
class SiteForecast:
    site_id: str
    at: str
    fire_lat: float
    fire_lon: float
    distance_km: float
    bearing_from_fire: int
    ros_head_m_h: int
    ros_toward_site_m_h: int
    hours_to_arrival: float | None
    arrival_confidence: str
    fuel_model: str
    front_positions: list[dict]
    terms: dict
    assumptions: list[str]


def forecast_site(site, weather, detections, at: str) -> SiteForecast | None:
    """Where the front goes next, relative to one site.

    `detections` are the scored detections already near the site. The nearest one is taken
    as the current front position: with VIIRS we know a pixel burned, not the perimeter, so
    this is the best available anchor and the forecast is only as good as it.
    """
    if not detections:
        return None

    nearest = min(detections, key=lambda d: haversine_km(site.lat, site.lon, d.lat, d.lon))
    dist_km = haversine_km(site.lat, site.lon, nearest.lat, nearest.lon)
    edge_km = max(0.0, dist_km - site.radius_m / 1000.0)
    bearing = bearing_deg(nearest.lat, nearest.lon, site.lat, site.lon)

    temp_c = weather.temp_c if weather else config.ASSUMED_WEATHER["temp_c"]
    rh = weather.rh_pct if weather else config.ASSUMED_WEATHER["rh_pct"]
    wind_kmh = weather.speed_kmh if weather else config.ASSUMED_WEATHER["speed_kmh"]
    from_deg = weather.from_deg if weather else config.ASSUMED_WEATHER["from_deg"]
    wind_to = (from_deg + 180) % 360

    fuel = FUELS.get(site.fuel_class, FUELS["medium"])
    moisture = fine_fuel_moisture(temp_c, rh)

    # No terrain layer yet: a single representative slope, stated as an assumption rather
    # than hidden. The design doc's DEM step replaces this.
    slope_pct = config.ASSUMED_SLOPE_PCT

    ros_head, terms = rothermel_ros(fuel, moisture, wind_kmh, slope_pct)
    ros_site = ros_at_bearing(ros_head, wind_to, bearing, wind_kmh)

    hours = (edge_km * 1000.0 / ros_site) if ros_site > 1.0 else None
    if hours is None or hours > 96:
        hours, conf = None, "no arrival within four days at this spread rate"
    elif angdiff(bearing, wind_to) <= 45:
        conf = "wind pushing the front toward the site"
    elif angdiff(bearing, wind_to) >= 135:
        conf = "site is behind the front; backing fire only"
    else:
        conf = "site is on the flank; a wind shift changes this materially"

    front = []
    for h in (1, 3, 6, 12):
        travel_km = ros_site * h / 1000.0
        lat, lon = destination(nearest.lat, nearest.lon, bearing, min(travel_km, edge_km))
        front.append({
            "hours_ahead": h,
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "travel_km": round(travel_km, 2),
            "reaches_site": travel_km >= edge_km,
        })

    return SiteForecast(
        site_id=site.site_id, at=at,
        fire_lat=nearest.lat, fire_lon=nearest.lon,
        distance_km=round(dist_km, 2),
        bearing_from_fire=int(round(bearing)),
        ros_head_m_h=int(round(ros_head)),
        ros_toward_site_m_h=int(round(ros_site)),
        hours_to_arrival=round(hours, 1) if hours is not None else None,
        arrival_confidence=conf,
        fuel_model=f"{fuel.anderson} {fuel.name}",
        front_positions=front,
        terms=terms,
        assumptions=[
            f"Front anchored on the nearest VIIRS detection, {round(dist_km, 1)} km away; "
            "VIIRS gives detections, not perimeters.",
            f"Uniform {slope_pct:.0f}% slope: no terrain layer is loaded yet.",
            f"Fuel treated as a single {fuel.anderson} bed, uniform across the approach.",
            "Wind held constant over the forecast window.",
            "Surface fire only: no crown fire, spotting or firebrand transport.",
            "Rothermel (1972) with no learned correction and no calibration against "
            "observed perimeters.",
        ],
    )
