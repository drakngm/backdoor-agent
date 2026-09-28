export type Env = 'PRODUCTION' | 'STAGING' | 'DEVELOPMENT'

export type ThreatLevel = 'LOW' | 'MEDIUM' | 'HIGH'
export type Verdict = 'CLEAN' | 'SUSPICIOUS' | 'BACKDOOR'
export type NodeState = 'running' | 'completed' | 'waiting' | 'error' | 'idle'

export interface HealthStatus {
  status: string
  app: string
  version: string
  uptime_seconds: number
  tools: string[]
  backend_connected: boolean
}

export interface DashboardMetrics {
  threat_level: ThreatLevel
  detection_confidence: number
  active_agents: number
  running_workflows: number
  detection_latency_ms: number
  detections_last_24h: number
  scan_strategy: string
}

export interface TrendSeries {
  [key: string]: number[]
}

export interface DetectionOverview {
  backdoors_detected: number
  backdoors_trend: number[]
  clean_models: number
  clean_models_trend: number[]
  models_analyzed: number
  models_analyzed_trend: number[]
}

export interface DagNode {
  id: string
  label: string
  sub: string
  group: string
  state: NodeState
}

export interface DagEdge {
  source: string
  target: string
  label?: string
}

export interface DagGraph {
  id: string
  nodes: DagNode[]
  edges: DagEdge[]
}

export interface TimelinePoint {
  t: string
  strip: number
  neural_cleanse: number
  activation_clustering: number
  overall: number
}

export interface DetectorStatus {
  name: string
  display: string
  description: string
  status: 'idle' | 'active' | 'error'
  last_run_ms: number
  detections: number
  precision: number
}

export interface MemorySummary {
  episodic: { entries: number; size_bytes: number }
  semantic: { entries: number; dims: number }
  procedural: { rules: number }
  last_consolidation: string
}

export interface TraceSummary {
  trace_id: string
  mode: 'agent' | 'workflow' | 'hybrid'
  status: string
  started_at: string
  duration_ms: number
  spans: number
}

export type SpanLevel = 'system' | 'data' | 'decision' | 'audit'

export interface Span {
  id: string
  parent_id?: string
  name: string
  span_type: string
  level: SpanLevel
  status: string
  duration_ms: number
  started_at: string
  input?: string
  output?: string
  hash?: string
  reasoning?: string
}

export interface LogEntry {
  time: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | 'TRACE'
  logger: string
  message: string
  trace_id?: string
}

export interface ThreatItem {
  id: string
  time: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  source: string
  summary: string
  detector: string
}

export interface SystemResource {
  cpu: number
  gpu: number
  mem: number
  gpu_name: string
}

export interface ExecuteResult {
  trace_id: string
  mode: string
  status: string
  strategy?: string
  verdict?: Verdict
  confidence?: number
  final_answer?: string
  spans?: Span[]
  decisions?: string[]
  tool_results?: Record<string, unknown>[]
  mermaid?: string
  critical_path?: string[]
  source: 'core' | 'mock'
}
