"""SQLAlchemy models based on ``design/DATABASE_ERD.md``.

Documented additions beyond the ERD:
* ``monitoring_session_devices`` links a session to the monitored devices
  (the ERD relationship required this join table to be explicit).
* Optional ``warnings``/``error_message``/``file_name`` columns make partial
  failures and report metadata visible without inventing measurements.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, unique=True, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    scan_links: Mapped[list["NetworkScanDevice"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    ping_tests: Mapped[list["PingTest"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    monitoring_observations: Mapped[list["MonitoringObservation"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    monitoring_links: Mapped[list["MonitoringSessionDevice"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    security_scans: Mapped[list["SecurityScan"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class NetworkScan(Base):
    __tablename__ = "network_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    network_cidr: Mapped[str] = mapped_column(String(64), nullable=False)
    interface_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)

    device_links: Mapped[list["NetworkScanDevice"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )


class NetworkScanDevice(Base):
    __tablename__ = "network_scan_devices"
    __table_args__ = (UniqueConstraint("scan_id", "device_id", name="uq_scan_device"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("network_scans.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    observation: Mapped[str] = mapped_column(String(32), default="not_tested", nullable=False)

    scan: Mapped["NetworkScan"] = relationship(back_populates="device_links")
    device: Mapped["Device"] = relationship(back_populates="scan_links")


class PingTest(Base):
    __tablename__ = "ping_tests"
    __table_args__ = (Index("ix_ping_tests_device_started", "device_id", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    probes_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    probes_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="ping_tests")
    probes: Mapped[list["PingProbe"]] = relationship(
        back_populates="ping_test", cascade="all, delete-orphan", order_by="PingProbe.sequence_number"
    )


class PingProbe(Base):
    __tablename__ = "ping_probes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ping_test_id: Mapped[int] = mapped_column(ForeignKey("ping_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    ping_test: Mapped["PingTest"] = relationship(back_populates="probes")


class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    device_links: Mapped[list["MonitoringSessionDevice"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    observations: Mapped[list["MonitoringObservation"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class MonitoringSessionDevice(Base):
    __tablename__ = "monitoring_session_devices"
    __table_args__ = (UniqueConstraint("session_id", "device_id", name="uq_monitoring_session_device"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)

    session: Mapped["MonitoringSession"] = relationship(back_populates="device_links")
    device: Mapped["Device"] = relationship(back_populates="monitoring_links")


class MonitoringObservation(Base):
    __tablename__ = "monitoring_observations"
    __table_args__ = (Index("ix_monitoring_observations_device_observed", "device_id", "observed_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    icmp_success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation: Mapped[str] = mapped_column(String(32), default="not_tested", nullable=False)

    session: Mapped["MonitoringSession"] = relationship(back_populates="observations")
    device: Mapped["Device"] = relationship(back_populates="monitoring_observations")


class SecurityScan(Base):
    __tablename__ = "security_scans"
    __table_args__ = (Index("ix_security_scans_device_started", "device_id", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    profile_name: Mapped[str] = mapped_column(String(64), default="common_services", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="security_scans")
    findings: Mapped[list["SecurityFinding"]] = relationship(
        back_populates="security_scan", cascade="all, delete-orphan"
    )


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    security_scan_id: Mapped[int] = mapped_column(
        ForeignKey("security_scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[str] = mapped_column(String(8), default="tcp", nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    service_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    security_scan: Mapped["SecurityScan"] = relationship(back_populates="findings")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="incidents")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    report_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="generating", nullable=False)
    range_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    range_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
