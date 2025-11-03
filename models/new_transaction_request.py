from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class NewTransactionRequest(BaseModel):
    requested_item_id: str = Field(
        ...,
        description="UUID of the requested item.",
        json_schema_extra={"example": "3f0a6a3c-6f34-4c11-9b3e-58b3b2cc0b9e"},
    )
    initiator_user_id: str = Field(
        ...,
        description="UUID of the initiator user.",
        json_schema_extra={"example": "1b2c3d4e-5f60-7a89-b0c1-d2e3f4a5b6c7"},
    )
    receiver_user_id: str = Field(
        ...,
        description="UUID of the receiver user.",
        json_schema_extra={"example": "7c6b5a4f-3e2d-1c0b-9a87-6f5e4d3c2b1a"},
    )
    type: Literal["trade", "purchase"] = Field(
        ...,
        description="Transaction type.",
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


