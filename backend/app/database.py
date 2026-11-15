"""Database engine/session setup for ECOSG.

Uses SQLite for the MVP so the whole stack runs with zero external
infrastructure. The schema is deliberately normalized (companies /
financial_metrics / esg_components as separate tables) so it maps
cleanly onto a real financial-data warehouse later (e.g. Postgres +
a nightly ETL from a market data + ESG data vendor).
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Vercel sets VERCEL=1; its function filesystem is read-only except /tmp,
# so the mock DB is reseeded there on each cold start.
DB_PATH = os.environ.get(
    "ECOSG_DB_PATH",
    "/tmp/ecosg.db" if os.environ.get("VERCEL")
    else os.path.join(os.path.dirname(os.path.dirname(__file__)), "ecosg.db"),
)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
