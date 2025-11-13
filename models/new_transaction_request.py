from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class NewTransactionRequest(BaseModel):
    type: Literal["trade", "purchase"] = Field(
        ...,
        description="Transaction type.",
        json_schema_extra={"example": "trade"},
    )
    offered_price: Optional[float] = Field(
        default=None,
        description="Optional offered price when type is purchase.",
        json_schema_extra={"example": 25.5},
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional initial message.",
        json_schema_extra={"example": "Can we meet this weekend?"},
    )
    status: Literal["pending", "accepted", "rejected", "canceled", "completed"] = Field(
        default="pending",
        description="Initial status for the transaction.",
        json_schema_extra={"example": "pending"},
    )
