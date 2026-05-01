from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


database_url_env = os.getenv("DATABASE_URL")

if database_url_env:
    DATABASE_URL = database_url_env
else:
    mysql_password = os.getenv("MYSQL_PASSWORD")
    if mysql_password:
        mysql_user = os.getenv("MYSQL_USER", "root")
        mysql_host = os.getenv("MYSQL_HOST", "127.0.0.1")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_db = os.getenv("MYSQL_DB", "rhino_gene")
        DATABASE_URL = (
            f"mysql+pymysql://{mysql_user}:{mysql_password}@"
            f"{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4"
        )
    else:
        DATABASE_URL = "sqlite:///./rhino.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
