from __future__ import annotations

import os
from typing import Optional, Literal
import uuid

from fastapi import FastAPI, HTTPException, status, Header
import mysql.connector
from pydantic import BaseModel, Field

from models.transaction import Transaction
from models.new_transaction_request import NewTransactionRequest

port = int(os.environ.get("FASTAPIPORT", 8000))


# -----------------------------------------------------------------------------
# FastAPI App Definition
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Transaction API",
    description="Am API to manage transactions.",
    version="1.0.0",
)


# -----------------------------------------------------------------------------
# Connect to db
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Transaction API",
    description="Am API to manage transactions.",
    version="1.0.0",
)
db_config = {
    "host": "136.113.127.151",          
    "user": "microservice_3",             
    "password": "arknights123",    
    "database": "neighborhood_db"          
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    print("✅ Database connected successfully")
    
    # Create transactions table if it doesn't exist
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id VARCHAR(36) PRIMARY KEY,
        requested_item_id VARCHAR(36) NOT NULL,
        initiator_user_id VARCHAR(36) NOT NULL,
        receiver_user_id VARCHAR(36) NOT NULL,
        type ENUM('trade', 'purchase') NOT NULL,
        offered_item_id VARCHAR(36) DEFAULT NULL,
        offered_price FLOAT DEFAULT NULL,
        status ENUM('pending', 'accepted', 'rejected', 'canceled', 'completed') NOT NULL DEFAULT 'pending',
        message TEXT DEFAULT NULL,
        idempotency_key VARCHAR(255) DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_idempotency_key (idempotency_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    cursor.execute(create_table_sql)
    conn.commit()
    print("✅ Table 'transactions' ensured to exist")
except Exception as e:
    print("❌ Database connection failed:", e)


def row_to_transaction(row: dict) -> Transaction:
    return Transaction(
        transaction_id=str(row["transaction_id"]),
        requested_item_id=str(row["requested_item_id"]),
        initiator_user_id=str(row["initiator_user_id"]),
        receiver_user_id=str(row["receiver_user_id"]),
        type=row["type"],
        offered_item_id=(str(row["offered_item_id"]) if row.get("offered_item_id") is not None else None),
        offered_price=row.get("offered_price"),
        status=row["status"],
        message=row.get("message"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class UpdateStatusRequest(BaseModel):
    status: Literal["accepted", "rejected", "canceled", "completed"] = Field(..., description="New status")


# -----------------------------------------------------------------------------
# Root Endpoint
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Welcome to the Transaction API. See /docs for details."}


# -----------------------------------------------------------------------------
# Transaction Endpoints
# -----------------------------------------------------------------------------
@app.post("/transactions/transaction", response_model=Transaction, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction: NewTransactionRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
):
    try:
        # Check if idempotency key is provided and if transaction already exists
        if x_idempotency_key:
            cursor.execute(
                "SELECT * FROM transactions WHERE idempotency_key = %s",
                (x_idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                # Return existing transaction (idempotent behavior)
                return row_to_transaction(existing)
        
        # Create new transaction
        new_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO transactions (transaction_id, requested_item_id, initiator_user_id, receiver_user_id, type, offered_item_id, offered_price, status, message, idempotency_key) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                new_id,
                transaction.requested_item_id,
                transaction.initiator_user_id,
                transaction.receiver_user_id,
                transaction.type,
                transaction.offered_item_id,
                transaction.offered_price,
                transaction.status,
                transaction.message,
                x_idempotency_key,
            ),
        )
        conn.commit()
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (new_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load created transaction")
        return row_to_transaction(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/transactions/{transaction_id}", response_model=Transaction)
def get_transaction(transaction_id: str):
    try:
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        return row_to_transaction(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/transactions", response_model=list[Transaction])
def list_transactions(
    status_param: Optional[Literal["pending", "accepted", "rejected", "canceled", "completed"]] = None,
    initiator_user_id: Optional[str] = None,
    receiver_user_id: Optional[str] = None,
    requested_item_id: Optional[str] = None,
    type: Optional[Literal["trade", "purchase"]] = None,
    limit: int = 50,
    offset: int = 0,
):
    try:
        conditions = []
        params: list = []
        if status_param is not None:
            conditions.append("status = %s")
            params.append(status_param)
        if initiator_user_id is not None:
            conditions.append("initiator_user_id = %s")
            params.append(initiator_user_id)
        if receiver_user_id is not None:
            conditions.append("receiver_user_id = %s")
            params.append(receiver_user_id)
        if requested_item_id is not None:
            conditions.append("requested_item_id = %s")
            params.append(requested_item_id)
        if type is not None:
            conditions.append("type = %s")
            params.append(type)

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM transactions{where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.append(limit)
        params.append(offset)
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [row_to_transaction(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/transactions/{transaction_id}", response_model=Transaction)
def update_transaction(transaction_id: str, payload: UpdateStatusRequest):
    try:
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        cursor.execute("UPDATE transactions SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE transaction_id = %s", (payload.status, transaction_id))
        conn.commit()
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
        updated = cursor.fetchone()
        return row_to_transaction(updated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete("/transactions/{transaction_id}", response_model=Transaction)
def delete_transaction(transaction_id: str):
    try:
        cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        cursor.execute("DELETE FROM transactions WHERE transaction_id = %s", (transaction_id,))
        conn.commit()
        return row_to_transaction(existing)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# -----------------------------------------------------------------------------
# Entrypoint for `python main.py`
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
