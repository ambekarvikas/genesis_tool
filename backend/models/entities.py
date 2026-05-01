from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Gene(Base):
    __tablename__ = "genes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gene_symbol: Mapped[str] = mapped_column(String(64), unique=True, index=True)


class Pathway(Base):
    __tablename__ = "pathways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kegg_id: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    system: Mapped[str] = mapped_column(String(64), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class GenePathwayMap(Base):
    __tablename__ = "gene_pathway_map"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gene_id: Mapped[int] = mapped_column(ForeignKey("genes.id"), index=True)
    pathway_id: Mapped[int] = mapped_column(ForeignKey("pathways.id"), index=True)
    impact_weight: Mapped[float] = mapped_column(Float, default=1.0)
    direction: Mapped[str] = mapped_column(String(16), default="up")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    age: Mapped[int] = mapped_column(Integer, default=0)
    gender: Mapped[str] = mapped_column(String(32), default="Unknown")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    system: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[float] = mapped_column(Float)


class PathwayScore(Base):
    __tablename__ = "pathway_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    pathway_id: Mapped[int] = mapped_column(ForeignKey("pathways.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    n_genes: Mapped[int] = mapped_column(Integer, default=0)
    median_fc: Mapped[float] = mapped_column(Float, default=0.0)


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    issue: Mapped[str] = mapped_column(String(255))
    impact: Mapped[str] = mapped_column(Text)
    action_json: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), index=True)
