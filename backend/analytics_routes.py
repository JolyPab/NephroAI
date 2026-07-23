"""First-party, low-PII acquisition events used by the admin funnel."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.database import AnalyticsEvent
from backend.deps import get_db


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class AnalyticsEventRequest(BaseModel):
    event: Literal["landing_view", "auth_view"]
    anonymous_id: str = Field(min_length=8, max_length=64)
    path: str = Field(default="/", max_length=255)
    source: str | None = Field(default=None, max_length=120)
    medium: str | None = Field(default=None, max_length=120)
    campaign: str | None = Field(default=None, max_length=160)
    click_id: str | None = Field(default=None, max_length=255)

    @field_validator("path")
    @classmethod
    def path_only(cls, value: str) -> str:
        value = value.strip()
        return value if value.startswith("/") else "/"


@router.post("/event", status_code=status.HTTP_202_ACCEPTED)
async def collect_event(payload: AnalyticsEventRequest, db: Session = Depends(get_db)):
    db.add(
        AnalyticsEvent(
            event_name=payload.event,
            anonymous_id=payload.anonymous_id,
            path=payload.path,
            source=payload.source,
            medium=payload.medium,
            campaign=payload.campaign,
            click_id=payload.click_id,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    return {"status": "accepted"}
