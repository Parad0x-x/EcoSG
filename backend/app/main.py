from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from .database import Base, engine
from .routers import companies, portfolio, quant
from .seed import seed

def schema_is_stale() -> bool:
    """True when the DB is missing a table or column the models expect,
    e.g. an ecosg.db created before a schema change. The DB holds only
    mock data, so the fix is a full reseed rather than a migration."""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing:
            return True
        columns = {c["name"] for c in inspector.get_columns(table.name)}
        if not set(table.columns.keys()) <= columns:
            return True
    return False


def ensure_seeded() -> None:
    if schema_is_stale():
        seed()
        return
    with engine.connect() as conn:
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM companies").scalar()
    if not count:
        seed()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_seeded()
    yield


app = FastAPI(
    title="ECOSG API",
    description=(
        "Sustainable investing API: financial metrics + an ESG scoring "
        "framework, exposed for single-stock lookup and portfolio screening. "
        "Demo data only -- not investment advice."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "ECOSG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(portfolio.router)
app.include_router(quant.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
