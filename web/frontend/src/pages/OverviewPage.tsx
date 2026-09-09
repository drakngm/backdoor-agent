import { useEffect, useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'
import Metric from '../components/ui/Metric'
import Sparkline from '../components/charts/Sparkline'
import TimelineChart, { SeriesLegend } from '../components/charts/TimelineChart'
import HoloCore from '../components/viz/HoloCore'
import DagGraph from '../components/viz/DagGraph'
import { api } from '../api/client'
import type { DashboardMetrics, DetectionOverview, DagGraph as DagGraphType, TimelinePoint } from '../types'

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [overview, setOverview] = useState<DetectionOverview | null>(null)
  const [dag, setDag] = useState<DagGraphType | null>(null)
  const [timeline, setTimeline] = useState<TimelinePoint[]>([])
  const [selectedNode, setSelectedNode] = useState<string>('')

  useEffect(() => {
    api.overview().then(({ metrics, overview }) => {
      setMetrics(metrics)
      setOverview(overview)
    })
    api.dag().then(setDag)
    api.timeline().then(setTimeline)
  }, [])

  if (!metrics || !overview || !dag) {
    return <div className="flex h-full items-center justify-center text-slate-600">Booting command center…</div>
  }

  const tlTone = metrics.threat_level === 'LOW' ? 'green' : metrics.threat_level === 'MEDIUM' ? 'amber' : 'red'

  return (
    <div className="fade-in mx-auto flex max-w-[1200px] flex-col gap-5">
      {/* ── Hero intelligence ───────────────────────────── */}
      <GlassCard className="relative overflow-hidden p-0" glow>
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(700px_400px_at_30%_50%,rgba(0,245,255,0.08),transparent_60%)]" />
        <div className="relative flex flex-col items-center gap-2 px-8 pt-6 text-center">
          <div className="text-[10px] font-semibold tracking-[0.3em] text-[#00f5ff] uppercase">Live Threat Assessment</div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-white">AI Backdoor Detection Command Center</h1>
          <div className="text-[12px] text-slate-400">Autonomous Detection · Analysis · Defense</div>
          <div className="mt-2 flex items-center gap-2">
            <Badge tone={tlTone} pulse>{metrics.threat_level} THREAT LEVEL</Badge>
            <Badge tone="cyan">{metrics.scan_strategy}</Badge>
          </div>
        </div>

        <div className="relative grid grid-cols-[280px_1fr] items-center gap-2 px-8 pt-2 pb-6">
          <div className="flex justify-center">
            <HoloCore size={250} className="float-y" />
          </div>
          <div className="grid grid-cols-2 gap-x-8 gap-y-5">
            <Metric
              label="Detection Confidence"
              value={metrics.detection_confidence}
              unit="%"
              tone="cyan"
              delta="↑ 1.2%"
            />
            <Metric
              label="Threat Level"
              value={metrics.threat_level}
              tone={tlTone}
              sub="3 detectors active"
            />
            <Metric
              label="Active Agents"
              value={metrics.active_agents}
              tone="purple"
              sub="hybrid loop running"
            />
            <Metric
              label="Detection Latency"
              value={metrics.detection_latency_ms}
              unit="ms"
              tone="blue"
              delta="↓ 18ms"
            />
            <Metric
              label="Running Workflows"
              value={metrics.running_workflows}
              tone="green"
              sub="DAG orchestration"
            />
            <Metric
              label="Detections 24h"
              value={metrics.detections_last_24h}
              tone="amber"
              delta="+1"
            />
          </div>
        </div>
      </GlassCard>

      {/* ── Detection overview cards ────────────────────── */}
      <div className="grid grid-cols-3 gap-5">
        <GlassCard hover className="relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">Backdoors Detected</span>
            <span className="digits text-[10px] text-[#ef4444]">+3.7%</span>
          </div>
          <div className="digits mt-2 text-3xl font-bold text-white">{overview.backdoors_detected.toLocaleString()}</div>
          <div className="mt-3"><Sparkline data={overview.backdoors_trend} color="#ef4444" /></div>
          <span className="absolute top-3 right-3 h-1.5 w-1.5 rounded-full bg-[#ef4444]/50 blur-[1px]" />
        </GlassCard>
        <GlassCard hover className="relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">Clean Models</span>
            <span className="digits text-[10px] text-[#22c55e]">+0.9%</span>
          </div>
          <div className="digits mt-2 text-3xl font-bold text-white">{overview.clean_models.toLocaleString()}</div>
          <div className="mt-3"><Sparkline data={overview.clean_models_trend} color="#22c55e" /></div>
          <span className="absolute top-3 right-3 h-1.5 w-1.5 rounded-full bg-[#22c55e]/50" />
        </GlassCard>
        <GlassCard hover className="relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">Models Analyzed</span>
            <span className="digits text-[10px] text-[#00f5ff]">+2.4%</span>
          </div>
          <div className="digits mt-2 text-3xl font-bold text-white">{overview.models_analyzed.toLocaleString()}</div>
          <div className="mt-3"><Sparkline data={overview.models_analyzed_trend} color="#00f5ff" /></div>
          <span className="absolute top-3 right-3 h-1.5 w-1.5 rounded-full bg-[#00f5ff]/50" />
        </GlassCard>
      </div>

      {/* ── Live hybrid agent DAG ───────────────────────── */}
      <GlassCard className="overflow-hidden p-0">
        <div className="flex items-center justify-between border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div>
            <h2 className="text-[13px] font-bold text-white">Live Hybrid Agent Workflow</h2>
            <p className="text-[11px] text-slate-500">Agent Loop → DAG orchestration · trace {dag.id}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 text-[10px] text-[#00f5ff]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#00f5ff] dot-pulse" /> RUNNING
            </span>
            <Badge tone="green">6/6 nodes</Badge>
          </div>
        </div>
        <div className="p-3">
          <DagGraph graph={dag} onSelect={setSelectedNode} />
          {selectedNode && (
            <div className="glass-inner mx-5 mb-3 mt-1 px-4 py-2 font-mono text-[10px] text-[#7dd3fc]">
              › node selected: <span className="text-[#00f5ff]">{selectedNode}</span>
            </div>
          )}
        </div>
      </GlassCard>

      {/* ── Detection timeline ──────────────────────────── */}
      <GlassCard className="p-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div>
            <h2 className="text-[13px] font-bold text-white">Detection Timeline</h2>
            <p className="text-[11px] text-slate-500">Last 10h · detector activity stream</p>
          </div>
          <SeriesLegend />
        </div>
        <div className="p-4">
          <TimelineChart data={timeline} height={250} />
        </div>
      </GlassCard>
    </div>
  )
}