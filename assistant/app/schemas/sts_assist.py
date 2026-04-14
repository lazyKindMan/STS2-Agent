"""Schemas for STS assistant API."""

from typing import Optional

from pydantic import BaseModel

from assistant.app.schemas.sts_state import (
    STSAssistGraphState,
    STSDecision,
)


class STSAssistRequest(STSAssistGraphState):
    """Request payload for STS assistant endpoint."""


class STSAssistResponse(BaseModel):
    """Response payload for STS assistant endpoint."""

    decision: Optional[STSDecision] = None
    state: STSAssistGraphState
