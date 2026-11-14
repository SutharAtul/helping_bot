"""Pydantic schemas for health and readiness endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional
from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    """Status details for an external or backing dependency."""

    status: str = Field(..., description="Dependency health state (healthy, unhealthy, unreachable)")
    message: Optional[str] = Field(None, description="Optional diagnostic message")


class HealthCheckResponse(BaseModel):
    """Full health check status response."""

    status: str = Field(..., description="Overall service status (healthy, degraded, unhealthy)")
    service: str = Field(..., description="Service identifier")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment name")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check",
    )
    dependencies: Dict[str, DependencyStatus] = Field(
        default_factory=dict,
        description="Health states of external dependencies",
    )


class LivenessResponse(BaseModel):
    """Liveness probe response model."""

    status: str = Field("alive", description="Process liveness state")
    service: str = Field(..., description="Service identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the probe",
    )


class ReadinessResponse(BaseModel):
    """Readiness probe response model."""

    status: str = Field(..., description="Overall readiness state (ready, not_ready)")
    service: str = Field(..., description="Service identifier")
    dependencies: Dict[str, DependencyStatus] = Field(
        default_factory=dict,
        description="Readiness of core dependencies",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the probe",
    )

