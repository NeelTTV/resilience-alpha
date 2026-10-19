import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, create_engine, select, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from services.common.config import secret
from services.common.security import current_user
from services.common.telemetry import instrument


def database_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    return URL.create(
        "postgresql+psycopg", username="resilience", password=secret("POSTGRES_PASSWORD"),
        host=os.getenv("DB_HOST", "db"), database="resilience",
    )


engine = create_engine(database_url(), pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


@asynccontextmanager
async def lifespan(app: FastAPI):
    secret("JWT_SECRET")
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


app = FastAPI(title="Resilience Alpha - Simulated Payments", lifespan=lifespan)
instrument(app, "payment")


class PaymentInput(BaseModel):
    amount_cents: int = Field(strict=True, gt=0, le=100_000_000)
    currency: str = Field(default="EUR", pattern="^EUR$")


class PaymentOutput(PaymentInput):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_at: datetime


def session():
    with Session(engine) as db:
        yield db


@app.get("/health")
def health(db: Session = Depends(session)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "payment", "database": "ok"}


@app.get("/transactions", response_model=list[PaymentOutput])
def transactions(user: str = Depends(current_user), db: Session = Depends(session)):
    return db.scalars(
        select(Transaction).where(Transaction.owner == user)
        .order_by(Transaction.created_at.desc()).limit(100)
    ).all()


@app.post("/transactions", response_model=PaymentOutput, status_code=201)
def pay(
    body: PaymentInput,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    user: str = Depends(current_user),
    db: Session = Depends(session),
):
    def existing():
        previous = db.scalar(select(Transaction).where(
            Transaction.idempotency_key == idempotency_key,
        ))
        if previous and (
            previous.owner != user or previous.amount_cents != body.amount_cents
            or previous.currency != body.currency
        ):
            raise HTTPException(409, "Idempotency key already used with different data")
        return previous

    if previous := existing():
        return previous
    transaction = Transaction(
        id=str(uuid.uuid4()), owner=user, idempotency_key=idempotency_key,
        amount_cents=body.amount_cents, currency=body.currency,
        created_at=datetime.now(timezone.utc), status="completed",
    )
    db.add(transaction)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if previous := existing():
            return previous
        raise
    db.refresh(transaction)
    return transaction

