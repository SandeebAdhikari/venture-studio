"""Provisional founder capability profiles (pre Founder Profile V2)."""

from __future__ import annotations

from typing import TypedDict

from app.founder_fit.capability_families import CAPABILITY_FAMILIES


class FounderCapabilitiesProfile(TypedDict):
    web_fullstack: int
    backend_api: int
    python_data: int
    database_storage: int
    payments_billing: int
    fraud_risk_ops: int
    security_engineering: int
    devops_cicd: int
    cloud_infra_compute: int
    ai_ml_operations: int
    agent_tooling: int
    compliance_regulatory: int


PROVISIONAL_DEFAULT_PROFILE: FounderCapabilitiesProfile = {
    "web_fullstack": 85,
    "backend_api": 80,
    "python_data": 75,
    "database_storage": 70,
    "payments_billing": 20,
    "fraud_risk_ops": 15,
    "security_engineering": 25,
    "devops_cicd": 65,
    "cloud_infra_compute": 55,
    "ai_ml_operations": 60,
    "agent_tooling": 80,
    "compliance_regulatory": 10,
}

FULL_COVERAGE_PROFILE: FounderCapabilitiesProfile = dict.fromkeys(CAPABILITY_FAMILIES, 100)  # type: ignore[misc]
