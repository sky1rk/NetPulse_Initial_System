"""Application settings.

Values can be overridden with ``NETPULSE_*`` environment variables or a
``.env`` file in the repository root / backend directory.  Only local-first
defaults are provided; no cloud services or authentication are configured.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NETPULSE_",
        env_file=(str(PROJECT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NetPulse"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    environment: str = "development"
    log_level: str = "INFO"

    data_dir: Path = BACKEND_DIR / "data"
    database_url: str = ""
    reports_dir: Path | None = None

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Discovery limits.
    max_scan_hosts: int = 256
    scan_concurrency: int = 32
    scan_ping_timeout_ms: int = 600
    allow_custom_scan_range: bool = False

    # Connectivity limits.
    ping_default_count: int = 5
    ping_max_count: int = 20
    ping_default_timeout_ms: int = 1000
    ping_min_timeout_ms: int = 100
    ping_max_timeout_ms: int = 5000

    # Monitoring limits.
    monitoring_default_interval_seconds: int = 10
    monitoring_min_interval_seconds: int = 5
    monitoring_max_interval_seconds: int = 3600

    # Security assessment limits.
    security_timeout_ms: int = 800
    security_max_concurrency: int = 4
    allowed_ports: str = "21,22,23,25,53,80,110,143,443,445,3306,3389,8080"

    # Analytics / health score thresholds.
    latency_good_ms: float = 50.0
    latency_fair_ms: float = 100.0
    latency_poor_ms: float = 200.0
    packet_loss_warning_percent: float = 20.0
    high_latency_warning_ms: float = 150.0
    icmp_failure_threshold: int = 3
    state_change_threshold: int = 3
    analytics_default_window_hours: int = 24

    def model_post_init(self, __context: object) -> None:  # noqa: D401
        """Create data directories and derive default paths."""
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.database_url:
            self.database_url = f"sqlite:///{(self.data_dir / 'netpulse.db').as_posix()}"
        if self.reports_dir is None:
            self.reports_dir = self.data_dir / "reports"
        self.reports_dir = Path(self.reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_port_list(self) -> list[int]:
        ports: list[int] = []
        for value in self.allowed_ports.split(","):
            value = value.strip()
            if value.isdigit():
                ports.append(int(value))
        return ports


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()


settings = get_settings()
