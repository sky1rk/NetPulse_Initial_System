/** API response types mirroring backend/app/schemas. */

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  database: string;
  timestamp: string;
}

export interface InterfaceCandidate {
  interface_name: string | null;
  local_ipv4: string | null;
  subnet_mask: string | null;
  network_cidr: string | null;
  is_up: boolean | null;
}

export interface NetworkInfo {
  interface_name: string | null;
  local_ipv4: string | null;
  subnet_mask: string | null;
  network_cidr: string | null;
  default_gateway: string | null;
  warnings: string[];
  candidates: InterfaceCandidate[];
}

export interface ScanDevice {
  id: number;
  ip_address: string;
  mac_address: string | null;
  hostname: string | null;
  observation: string;
  last_seen: string;
}

export interface ScanResponse {
  scan_id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  network_cidr: string;
  discovered_count: number;
  devices: ScanDevice[];
  warnings: string[];
}

export interface Device {
  id: number;
  ip_address: string;
  mac_address: string | null;
  hostname: string | null;
  vendor: string | null;
  first_seen: string;
  last_seen: string;
  created_at: string;
  updated_at: string;
  latest_observation: string;
  latest_latency_ms: number | null;
  latest_observation_at: string | null;
  latest_packet_loss_percent: number | null;
}

export interface DeviceList {
  items: Device[];
  total: number;
  limit: number;
  offset: number;
}

export interface PingTestSummary {
  id: number;
  started_at: string;
  completed_at: string | null;
  probes_sent: number;
  probes_received: number;
  packet_loss_percent: number | null;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  status: string;
}

export interface ObservationSummary {
  id: number;
  session_id: number;
  observed_at: string;
  icmp_success: boolean;
  latency_ms: number | null;
  observation: string;
}

export interface SecurityScanSummary {
  id: number;
  started_at: string;
  completed_at: string | null;
  profile_name: string;
  status: string;
}

export interface DeviceDetail extends Device {
  recent_ping_tests: PingTestSummary[];
  recent_observations: ObservationSummary[];
  recent_security_scans: SecurityScanSummary[];
}

export interface PingProbe {
  sequence_number: number;
  success: boolean;
  latency_ms: number | null;
  tested_at: string;
  error_message: string | null;
}

export interface PingTestResponse {
  test_id: number;
  device_id: number;
  probes_sent: number;
  probes_received: number;
  packet_loss_percent: number | null;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  jitter_ms: number | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  probes: PingProbe[];
  message: string | null;
}

export interface MonitoringObservation {
  id: number;
  session_id: number;
  device_id: number;
  observed_at: string;
  icmp_success: boolean;
  latency_ms: number | null;
  observation: string;
}

export interface MonitoringSession {
  session_id: number;
  status: string;
  interval_seconds: number;
  started_at: string;
  ended_at: string | null;
  device_ids: number[];
  observation_count: number;
  success_count: number;
  failure_count: number;
  availability_percent: number | null;
  latest_observation_at: string | null;
  observations?: MonitoringObservation[];
  note?: string;
}

export interface HealthThresholds {
  good_ms: number;
  fair_ms: number;
  poor_ms: number;
}

export interface HealthScore {
  score: number;
  latency_score: number;
  packet_loss_score: number;
  availability_score: number;
  thresholds: HealthThresholds;
  label: string;
}

export interface AnalyticsSummary {
  device_id: number | null;
  window_from: string;
  window_to: string;
  sample_count: number;
  successful_samples: number;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  packet_loss_percent: number | null;
  jitter_ms: number | null;
  observation_count: number;
  successful_observations: number;
  availability_percent: number | null;
  health_score: HealthScore | null;
  notes: string[];
}

export interface HistoryPoint {
  timestamp: string;
  device_id: number;
  latency_ms: number | null;
  success: boolean;
  observation: string;
  source: string;
}

export interface HistoryResponse {
  device_id: number | null;
  window_from: string;
  window_to: string;
  points: HistoryPoint[];
  sample_count: number;
  success_count: number;
  notes: string[];
}

export interface PortInfo {
  port: number;
  service_name: string;
  note: string | null;
}

export interface SecurityProfile {
  name: string;
  description: string;
  ports: PortInfo[];
}

export interface SecurityFinding {
  id: number | null;
  port: number;
  protocol: string;
  state: string;
  service_name: string | null;
  severity: string;
  recommendation: string | null;
}

export interface SecurityScanResponse {
  scan_id: number;
  device_id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  profile_name: string;
  findings: SecurityFinding[];
  disclaimer: string;
  warnings: string[];
}

export interface SecurityFindingRecord extends SecurityFinding {
  id: number;
  scan_id: number;
  device_id: number;
  device_ip: string;
  scanned_at: string;
  scan_status: string;
}

export interface SecurityFindingsList {
  items: SecurityFindingRecord[];
  total: number;
  limit: number;
  offset: number;
  disclaimer: string;
}

export interface Recommendation {
  rule_id: string;
  title: string;
  severity: string;
  observed_condition: string;
  recommendation: string;
  created_at: string;
  device_id: number | null;
  device_ip: string | null;
  evidence: Record<string, unknown> | null;
}

export interface RecommendationsResponse {
  items: Recommendation[];
  generated_at: string;
  note: string;
}

export interface ReportRecord {
  id: number;
  generated_at: string;
  report_type: string;
  status: string;
  file_name: string | null;
  range_from: string | null;
  range_to: string | null;
  error_message: string | null;
  download_url: string | null;
}

export interface ReportList {
  items: ReportRecord[];
  total: number;
}

export interface TopologyNode {
  id: string;
  label: string;
  node_type: string;
  ip_address: string | null;
  mac_address: string | null;
  observation: string | null;
  inferred: boolean;
}

export interface TopologyEdge {
  source: string;
  target: string;
  label: string | null;
  inferred: boolean;
}

export interface TopologyResponse {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  local_host: TopologyNode | null;
  warnings: string[];
  note: string;
}

export interface ActivityItem {
  activity_type: string;
  title: string;
  description: string;
  timestamp: string;
  status: string | null;
}

export interface DashboardSummary {
  devices_total: number;
  responding_hosts: number;
  no_icmp_hosts: number;
  not_tested_hosts: number;
  avg_latency_ms: number | null;
  packet_loss_percent: number | null;
  health_score: HealthScore | null;
  health_label: string;
  last_scan_at: string | null;
  latest_observation_at: string | null;
  active_monitoring_sessions: number;
  open_security_findings: number;
  reports_count: number;
  recent_activity: ActivityItem[];
  warnings: string[];
}
