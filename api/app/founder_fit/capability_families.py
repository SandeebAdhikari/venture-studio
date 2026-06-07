"""Approved capability families from FF-CM-1."""

from __future__ import annotations

from typing import Final

CAPABILITY_FAMILIES: Final[frozenset[str]] = frozenset(
    {
        "web_fullstack",
        "backend_api",
        "python_data",
        "database_storage",
        "payments_billing",
        "fraud_risk_ops",
        "security_engineering",
        "devops_cicd",
        "cloud_infra_compute",
        "ai_ml_operations",
        "agent_tooling",
        "compliance_regulatory",
    }
)
