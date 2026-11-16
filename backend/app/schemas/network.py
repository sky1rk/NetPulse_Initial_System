"""Network information, discovery and topology schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UtcDateTime


class InterfaceCandidate(BaseModel):
    interface_name: str | None = None
    local_ipv4: str | None = None
    subnet_mask: str | None = None
    network_cidr: str | None = None
    is_up: bool | None = None


class NetworkInfoResponse(BaseModel):
    interface_name: str | None = None
    local_ipv4: str | None = None
    subnet_mask: str | None = None
    network_cidr: str | None = None
    default_gateway: str | None = None
    warnings: list[str] = Field(default_factory=list)
    candidates: list[InterfaceCandidate] = Field(default_factory=list)


class ScanRequest(BaseModel):
    network_cidr: str | None = Field(
        default=None,
        description="CIDR to scan. Defaults to the detected local subnet when omitted.",
    )
    confirm_authorized: bool = False


class ScanDeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    observation: str
    last_seen: UtcDateTime


class ScanResponse(BaseModel):
    scan_id: int
    status: str
    started_at: UtcDateTime
    completed_at: UtcDateTime | None = None
    network_cidr: str
    discovered_count: int
    devices: list[ScanDeviceOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TopologyNode(BaseModel):
    id: str
    label: str
    node_type: str
    ip_address: str | None = None
    mac_address: str | None = None
    observation: str | None = None
    inferred: bool = False


class TopologyEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    inferred: bool = True


class TopologyResponse(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)
    local_host: TopologyNode | None = None
    warnings: list[str] = Field(default_factory=list)
    note: str = (
        "Logical view based on available network information; physical links are not verified."
    )
