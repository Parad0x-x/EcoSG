from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from .database import Base, engine
from .routers import companies, portfolio, quant
from .seed import seed

app = FastAPI(
    title="ECOSG API",
    description=(
        "Sustainable investing API: financial metrics + an ESG scoring "
        "framework, exposed for single-stock lookup and portfolio screening. "
        "Demo data only -- not investment advice."
    ),
    version="0.1.0",
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


@app.on_event("startup")
def ensure_seeded() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "companies" not in inspector.get_table_names():
        seed()
        return
    with engine.connect() as conn:
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM companies").scalar()
    if not count:
        seed()


@app.get("/api/health")
def health():
    return {"status": "ok"}
