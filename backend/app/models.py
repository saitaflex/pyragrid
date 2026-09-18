"""models.py — Pydantic v2 mirrors of TEAM_PLAN.md §2.4 (identical field names)."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel

Level = Literal["NORMAL", "ELEVATED", "HIGH", "CRITICAL"]
SiteType = Literal[
    "solar_farm", "wind_farm", "substation", "forest_block", "telecom_tower", "test_plot"
]
FuelClass = Literal["low", "medium", "high", "very_high"]
RouteStatus = Literal["available", "potentially_exposed"]
DataSource = Literal["firms_sp", "firms_nrt", "synthetic_fallback"]
FactorStatus = Literal["observed", "customer_provided", "assumed", "unknown"]
SourceState = Literal["ONLINE", "FALLBACK", "OFFLINE", "NOT_CONFIGURED"]
Role = Literal["admin", "operator"]
Audience = Literal["operator", "site_team", "fire_service_liaison"]
AdvisorEngine = Literal["groq", "ollama", "template"]
Decision = Literal["approved", "rejected"]


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    contract_version: Literal["2.1.0"] = "2.1.0"
    model_version: Literal["rules-1.0"] = "rules-1.0"
    data_source: DataSource
    replay_start: str
    replay_end: str
    step_hours: Literal[3] = 3


class User(BaseModel):
    email: str
    name: str
    customer_id: str
    role: Role


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: User


class Component(BaseModel):
    name: str
    value_eur: int


class Site(BaseModel):
    site_id: str
    name: str
    type: SiteType
    lat: float
    lon: float
    radius_m: int
    value_eur: int
    fuel_class: FuelClass
    personnel_on_site: int
    primary_access_bearing_deg: int
    criticality: int  # 1..5
    components: list[Component]


class RejectedRow(BaseModel):
    row: int
    site_id: Optional[str]
    reason: str


class ImportReport(BaseModel):
    accepted: int
    rejected: list[RejectedRow]
    total_sites: int


class Factors(BaseModel):
    proximity: Optional[float]       # 0..35
    wind_alignment: Optional[float]  # 0..25
    weather: Optional[float]         # 0..15
    fuel: Optional[float]            # 0..15
    vulnerability: Optional[float]   # 0..10


class FactorStatuses(BaseModel):
    proximity: FactorStatus
    wind_alignment: FactorStatus
    weather: FactorStatus
    fuel: FactorStatus
    vulnerability: FactorStatus


class AccessRoute(BaseModel):
    name: Literal["Primary access", "Secondary access"]
    bearing_deg: int
    status: RouteStatus


class Wind(BaseModel):
    speed_kmh: float
    from_deg: int
    to_deg: int


class Weather(BaseModel):
    temp_c: float
    rh_pct: float


class SiteStatus(BaseModel):
    site_id: str
    name: str
    type: SiteType
    lat: float
    lon: float
    radius_m: int
    value_eur: int
    personnel_on_site: int
    criticality: int
    score: int
    level: Level
    model_version: Literal["rules-1.0"] = "rules-1.0"
    factors: Factors
    factor_status: FactorStatuses
    nearest_fire_km: Optional[float]
    fire_bearing_deg: Optional[int]
    fire_moving_toward_site: Optional[bool]
    triggering_detection_id: Optional[str]
    wind: Optional[Wind]
    weather: Optional[Weather]
    access_routes: list[AccessRoute]
    exposed_components: list[Component]
    sop_actions: list[str]


class PortfolioCounts(BaseModel):
    NORMAL: int
    ELEVATED: int
    HIGH: int
    CRITICAL: int


class Portfolio(BaseModel):
    at: str
    counts: PortfolioCounts
    total_exposed_value_eur: int
    sites: list[SiteStatus]


class Detection(BaseModel):
    id: str
    source: DataSource
    external_id: Optional[str]
    lat: float
    lon: float
    observed_at: str
    received_at: str
    satellite: str
    confidence: Literal["n", "h"]
    intensity_frp: float


class Alert(BaseModel):
    alert_id: str
    site_id: str
    site_name: str
    at: str
    kind: Literal["escalation", "de-escalation"]
    from_level: Level
    to_level: Level
    score: int
    headline: str
    triggering_detection_id: Optional[str]
    factors: Factors
    factor_status: FactorStatuses
    model_version: Literal["rules-1.0"] = "rules-1.0"
    processed_at: str
    actions: list[str]
    rule_ids: list[str]
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]


class AckResponse(BaseModel):
    alert_id: str
    acknowledged: Literal[True] = True
    acknowledged_by: str
    acknowledged_at: str


class Incident(BaseModel):
    incident_id: str
    site_id: str
    site_name: str
    level: Literal["HIGH", "CRITICAL"]
    score: int
    opened_at: str
    closed_at: Optional[str]
    headline: str
    actions: list[str]
    rule_ids: list[str]
    disclaimer: str


class SopConditions(BaseModel):
    min_level: Level
    asset_types: list[SiteType]
    min_criticality: int
    wind_toward_site: Optional[bool]


class SopRule(BaseModel):
    rule_id: str
    name: str
    enabled: bool
    priority: int
    conditions: SopConditions
    actions: list[str]


class SopRuleInput(BaseModel):
    name: str
    enabled: bool
    priority: int
    conditions: SopConditions
    actions: list[str]


class TimelinePoint(BaseModel):
    at: str
    score: int
    level: Level
    nearest_fire_km: Optional[float]


class ReplaySummary(BaseModel):
    start: str
    end: str
    step_hours: Literal[3] = 3
    data_source: DataSource
    model_version: Literal["rules-1.0"] = "rules-1.0"
    total_detections: int
    detections_used: int
    alerts_raised: int
    incidents: int
    sites_ever_high: int
    sites_ever_critical: int
    sites_reached_by_fire: int
    missed_exposures: int
    median_lead_time_hours: Optional[float]
    explanation_coverage_pct: float


class SourceStatus(BaseModel):
    name: Literal["FIRMS", "Weather", "Vegetation", "Notification", "Database", "AI Advisor"]
    state: SourceState
    detail: str


class IngestionRun(BaseModel):
    run_id: str
    source: str
    started_at: str
    completed_at: Optional[str]
    records_received: int
    records_inserted: int
    records_rejected: int
    error_message: Optional[str]


class AuditEntry(BaseModel):
    id: int
    at: str
    actor: str
    action: str
    details: str


class OutboxEmail(BaseModel):
    alert_id: str
    to: str
    subject: str
    body: str
    channel: Literal["email"] = "email"
    status: Literal["outbox", "sent", "failed"]


class AdvisorSuggestion(BaseModel):
    suggestion_id: str
    title: str
    detail: str
    audience: Audience
    priority: Literal[1, 2, 3]
    evidence: list[str]
    decision: Optional[Decision]
    decided_by: Optional[str]
    decided_at: Optional[str]


class AdvisorResponse(BaseModel):
    incident_id: str
    at: str
    generated_by: AdvisorEngine
    model: Optional[str]
    created_at: str
    evidence_keys: list[str]
    suggestions: list[AdvisorSuggestion]
    rejected_by_guardrails: int
    fallback_reason: Optional[str]
    disclaimer: str


class DecisionRequest(BaseModel):
    decision: Decision
    note: str


class DecisionRecord(BaseModel):
    suggestion_id: str
    incident_id: str
    title: str
    decision: Decision
    note: str
    decided_by: str
    decided_at: str
    generated_by: AdvisorEngine


class Hazard(BaseModel):
    name: str
    kind: Literal["electrical", "battery", "fuel_oil", "height", "none"]
    note: str


class WaterPoint(BaseModel):
    name: str
    lat: float
    lon: float
    capacity_m3: int


class Contact(BaseModel):
    role: str
    phone: str


class HandoffPack(BaseModel):
    site_id: str
    site_name: str
    type: SiteType
    at: str
    generated_at: str
    lat: float
    lon: float
    level: Level
    score: int
    headline: str
    personnel_on_site: int
    criticality: int
    access_routes: list[AccessRoute]
    hazards: list[Hazard]
    water_points: list[WaterPoint]
    contact: Contact
    simulated: Literal[True] = True
    disclaimer: str
