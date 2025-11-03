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
    requested_item_id: str = Field(
        ...,
        description="The UUID of the item being requested by the initiator.",
        json_schema_extra={"example": "3f0a6a3c-6f34-4c11-9b3e-58b3b2cc0b9e"},
    )
    initiator_user_id: str = Field(
        ...,
        description="The UUID of the user who started the transaction.",
        json_schema_extra={"example": "1b2c3d4e-5f60-7a89-b0c1-d2e3f4a5b6c7"},
    )
    receiver_user_id: str = Field(
        ...,
        description="The UUID of the user who owns the requested item.",
        json_schema_extra={"example": "7c6b5a4f-3e2d-1c0b-9a87-6f5e4d3c2b1a"},
    )
    type: Literal["trade", "purchase"] = Field(
        ...,
        description="The transaction type.",
        json_schema_extra={"example": "trade"},
    )
    offered_item_id: Optional[str] = Field(
        default=None,
        description="Optional offered item UUID when type is trade.",
        json_schema_extra={"example": "9eaa9a7c-4e3b-4c9f-8fb0-0ea9722c9b9c"},
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