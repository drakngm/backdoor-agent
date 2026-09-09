import type {
  HealthStatus,
  DashboardMetrics,
  DetectionOverview,
  DagGraph,
  TimelinePoint,
  DetectorStatus,
  MemorySummary,
  TraceSummary,
  LogEntry,
  ThreatItem,
  SystemResource,
  ExecuteResult,
} from '../types'
import * as mock from './mock'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function request<T>(path: string, init?: RequestInit, timeoutMs = 6000): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...init, signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

export class Api {
  async health(): Promise<HealthStatus> {
    try {
      return await request<HealthStatus>('/health')
    } catch {
      return mock.mockHealth
    }
  }

  async overview(): Promise<{ metrics: DashboardMetrics; overview: DetectionOverview }> {
    try {
      const [metrics, overview] = await Promise.all([
        request<DashboardMetrics>('/dashboard/overview/metrics'),
        request<DetectionOverview>('/dashboard/overview'),
      ])
      return { metrics, overview }
    } catch {
      return { metrics: mock.mockMetrics, overview: mock.mockOverview }
    }
  }

  async dag(): Promise<DagGraph> {
    try {
      return await request<DagGraph>('/workflow/dag/live')
    } catch {
      return mock.mockDag
    }
  }

  async timeline(): Promise<TimelinePoint[]> {
    try {
      return await request<TimelinePoint[]>('/detection/timeline')
    } catch {
      return mock.mockTimeline()
    }
  }

  async detectors(): Promise<DetectorStatus[]> {
    try {
      return await request<DetectorStatus[]>('/detection/detectors')
    } catch {
      return mock.mockDetectors
    }
  }

  async memory(): Promise<MemorySummary> {
    try {
      return await request<MemorySummary>('/memory/stats')
    } catch {
      return mock.mockMemory
    }
  }

  async traces(): Promise<TraceSummary[]> {
    try {
      return await request<TraceSummary[]>('/traces')
    } catch {
      return mock.mockTraces
    }
  }

  async logs(): Promise<LogEntry[]> {
    try {
      return await request<LogEntry[]>('/logs')
    } catch {
      return mock.mockLogs
    }
  }

  async threats(): Promise<ThreatItem[]> {
    try {
      return await request<ThreatItem[]>('/threats')
    } catch {
      return mock.mockThreats
    }
  }

  async resources(): Promise<SystemResource> {
    try {
      return await request<SystemResource>('/system/resources')
    } catch {
      return mock.mockResource
    }
  }

  async execute(mode: 'agent' | 'workflow' | 'hybrid', body: Record<string, string>): Promise<ExecuteResult> {
    try {
      return await request<ExecuteResult>(`/execute/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }, 60000)
    } catch {
      return { ...mock.runExecute(mode, body), source: 'mock' }
    }
  }
}

export const api = new Api()