from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    transaction_id: str = Field(
        ...,
        description="The unique identifier for the transaction (UUID).",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    type: Literal["trade", "purchase"] = Field(
        ...,
        description="The transaction type.",
        json_schema_extra={"example": "trade"},
    )
    offered_price: Optional[float] = Field(
        default=None,
        description="Optional offered price when type is purchase.",
        json_schema_extra={"example": 25.5},
    )
    status: Literal["pending", "accepted", "rejected", "canceled", "completed"] = Field(
        ...,
        description="The current status of the transaction.",
        json_schema_extra={"example": "pending"},
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional message attached to the transaction.",
        json_schema_extra={"example": "Can we meet this weekend?"},
    )
    created_at: datetime = Field(
        ...,
        description="The timestamp when the transaction was created.",
        json_schema_extra={"example": "2023-01-01T00:00:00"},
    )
    updated_at: datetime = Field(
        ...,
        description="The timestamp when the transaction was last updated.",
        json_schema_extra={"example": "2023-01-01T00:00:00"},
    )
