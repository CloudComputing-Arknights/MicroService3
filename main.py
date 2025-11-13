from __future__ import annotations

import os
from typing import Optional, Literal
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Header, Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Text, DateTime, Enum, select, func
from pydantic import BaseModel, Field

from models.transaction import Transaction
from models.new_transaction_request import NewTransactionRequest

port = int(os.environ.get("FASTAPIPORT", 8000))


# -----------------------------------------------------------------------------
# FastAPI App Definition
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Transaction API",
    description="An API to manage transactions.",
    version="1.0.0",
)


# -----------------------------------------------------------------------------
# Database Configuration with SQLAlchemy
# -----------------------------------------------------------------------------
DATABASE_URL = "mysql+aiomysql://microservice_3:arknights123@136.113.127.151/neighborhood_db"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# -----------------------------------------------------------------------------
# SQLAlchemy Models
# -----------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


class TransactionDB(Base):
    __tablename__ = "transactions"
    
    transaction_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(Enum("trade", "purchase"), nullable=False)
    offered_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "rejected", "canceled", "completed"),
        nullable=False,
        default="pending"
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )


# -----------------------------------------------------------------------------
# Database Lifecycle
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_db():
    """Initialize database on startup"""
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized successfully")
        print("✅ Table 'transactions' ensured to exist")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")


@app.on_event("shutdown")
async def shutdown_db():
    """Close database connections on shutdown"""
    await engine.dispose()
    print("✅ Database connections closed")


# -----------------------------------------------------------------------------
# Dependency to get DB session
# -----------------------------------------------------------------------------
async def get_db():
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def db_to_transaction(db_transaction: TransactionDB) -> Transaction:
    """Convert SQLAlchemy model to Pydantic model"""
    return Transaction(
        transaction_id=db_transaction.transaction_id,
        type=db_transaction.type,
        offered_price=db_transaction.offered_price,
        status=db_transaction.status,
        message=db_transaction.message,
        created_at=db_transaction.created_at,
        updated_at=db_transaction.updated_at,
    )


class UpdateStatusRequest(BaseModel):
    status: Literal["accepted", "rejected", "canceled", "completed"] = Field(..., description="New status")


# -----------------------------------------------------------------------------
# Root Endpoint
# -----------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Welcome to the Transaction API. See /docs for details."}


@app.get("/ping-db")
async def ping_db(db: AsyncSession = Depends(get_db)):
    """Health check endpoint for database"""
    try:
        result = await db.execute(select(func.now()))
        db_time = result.scalar()
        return {"db_time": db_time}
    except Exception as e:
        return {"error": str(e)}


# -----------------------------------------------------------------------------
# Transaction Endpoints
# -----------------------------------------------------------------------------
@app.post("/transactions/transaction", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: NewTransactionRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if idempotency key is provided and if transaction already exists
        if x_idempotency_key:
            stmt = select(TransactionDB).where(TransactionDB.idempotency_key == x_idempotency_key)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                # Return existing transaction (idempotent behavior)
                return db_to_transaction(existing)
        
        # Create new transaction
        new_transaction = TransactionDB(
            transaction_id=str(uuid.uuid4()),
            type=transaction.type,
            offered_price=transaction.offered_price,
            status=transaction.status,
            message=transaction.message,
            idempotency_key=x_idempotency_key,
        )
        
        db.add(new_transaction)
        await db.commit()
        await db.refresh(new_transaction)
        
        return db_to_transaction(new_transaction)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(TransactionDB).where(TransactionDB.transaction_id == transaction_id)
        result = await db.execute(stmt)
        db_transaction = result.scalar_one_or_none()
        
        if not db_transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        
        return db_to_transaction(db_transaction)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/transactions", response_model=list[Transaction])
async def list_transactions(
    status_param: Optional[Literal["pending", "accepted", "rejected", "canceled", "completed"]] = None,
    type: Optional[Literal["trade", "purchase"]] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(TransactionDB)
        
        # Apply filters
        if status_param is not None:
            stmt = stmt.where(TransactionDB.status == status_param)
        if type is not None:
            stmt = stmt.where(TransactionDB.type == type)
        
        # Order and paginate
        stmt = stmt.order_by(TransactionDB.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        db_transactions = result.scalars().all()
        
        return [db_to_transaction(t) for t in db_transactions]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    payload: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(TransactionDB).where(TransactionDB.transaction_id == transaction_id)
        result = await db.execute(stmt)
        db_transaction = result.scalar_one_or_none()
        
        if not db_transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        
        # Update status
        db_transaction.status = payload.status
        
        await db.commit()
        await db.refresh(db_transaction)
        
        return db_to_transaction(db_transaction)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.delete("/transactions/{transaction_id}", response_model=Transaction)
async def delete_transaction(transaction_id: str, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(TransactionDB).where(TransactionDB.transaction_id == transaction_id)
        result = await db.execute(stmt)
        db_transaction = result.scalar_one_or_none()
        
        if not db_transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        
        # Store transaction data before deletion
        transaction_data = db_to_transaction(db_transaction)
        
        await db.delete(db_transaction)
        await db.commit()
        
        return transaction_data
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# -----------------------------------------------------------------------------
# Entrypoint for `python main.py`
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
