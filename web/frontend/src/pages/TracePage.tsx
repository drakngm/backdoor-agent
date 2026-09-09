import { useEffect, useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'
import { api } from '../api/client'
import type { TraceSummary, SpanLevel } from '../types'

const levels: { key: SpanLevel; label: string; color: string }[] = [
  { key: 'system', label: 'System', color: '#00f5ff' },
  { key: 'data', label: 'Data Flow', color: '#8b5cf6' },
  { key: 'decision', label: 'Decision CoT', color: '#3b82f6' },
  { key: 'audit', label: 'Audit', color: '#22c55e' },
]

const modeTone = { agent: 'cyan', workflow: 'blue', hybrid: 'purple' } as const

export default function TracePage() {
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [filter, setFilter] = useState<SpanLevel | 'all'>('all')

  useEffect(() => {
    api.traces().then(setTraces)
  }, [])

  return (
    <div className="fade-in mx-auto flex max-w-[1000px] flex-col gap-5">
      {/* level filter */}
      <GlassCard className="p-0">
        <div className="flex items-center gap-2 border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <span className="mr-2 text-[11px] font-bold tracking-wider text-slate-400 uppercase">Trace Levels</span>
          <button
            onClick={() => setFilter('all')}
            className={`rounded-lg px-3 py-1 text-[11px] font-medium transition-colors ${filter === 'all' ? 'bg-[rgba(0,245,255,0.1)] text-[#00f5ff]' : 'text-slate-400 hover:text-slate-200'}`}
          >
            All
          </button>
          {levels.map((l) => (
            <button
              key={l.key}
              onClick={() => setFilter(l.key)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-medium transition-colors ${filter === l.key ? 'bg-[rgba(0,245,255,0.1)] text-[#00f5ff]' : 'text-slate-400 hover:text-slate-200'}`}
            >
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: l.color }} />
              {l.label}
            </button>
          ))}
        </div>

        <div className="divide-y divide-[rgba(148,163,184,0.06)]">
          {traces.map((t) => (
            <div key={t.trace_id} className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-white/[0.02]">
              <span className={`h-8 w-1 rounded-full ${t.status === 'running' ? 'bg-[#00f5ff] animate-pulse' : 'bg-[#22c55e]'}`} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[12px] font-semibold text-[#7dd3fc]">{t.trace_id}</span>
                  <Badge tone={modeTone[t.mode]}>{t.mode}</Badge>
                </div>
                <div className="mt-0.5 text-[10px] text-slate-500">
                  {new Date(t.started_at).toLocaleString('zh-CN', { hour12: false })} · {t.spans} spans · {t.duration_ms}ms
                </div>
              </div>
              <div className="flex items-center gap-3 font-mono text-[10px]">
                {levels.map((l) => (
                  <span key={l.key} className="flex items-center gap-1 text-slate-500">
                    <span className="h-1 w-1 rounded-full" style={{ background: l.color, opacity: 0.7 }} />
                    {l.label.split(' ')[0]}
                  </span>
                ))}
              </div>
              <Badge tone={t.status === 'completed' ? 'green' : 'cyan'} pulse={t.status === 'running'}>{t.status}</Badge>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* CoT detail */}
      <GlassCard>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[11px] font-bold tracking-[0.14em] text-slate-300 uppercase">Decision Chain-of-Thought</h3>
          <Badge tone="blue">trc_9f2a11c4</Badge>
        </div>
        <div className="space-y-2 font-mono text-[11px]">
          {[
            ['system', 'span · model_analyzer — inspect @conv4_2 weights', '#00f5ff'],
            ['data', 'hash sha256:7a3f…c1be — activation tensor (no raw payload)', '#8b5cf6'],
            ['decision', 'STRIP confidence 0.93 → exceeds 0.6 gate', '#3b82f6'],
            ['decision', 'cross-validate with Neural Cleanse (trigger reverse)', '#3b82f6'],
            ['audit', 'event recorded · operator:system · policy v2.4', '#22c55e'],
            ['data', 'hash sha256:9d02…51ef — artifact report_v2.4.pdf', '#8b5cf6'],
          ].map(([lvl, msg, color], i) => (
            <div key={i} className="flex items-start gap-3">
              <span className={`digits mt-1 h-4 w-4 shrink-0 rounded text-center text-[8px] leading-4 font-bold ${lvl === 'audit' ? 'text-[#22c55e]' : 'text-[#7dd3fc]'} bg-white/[0.04]`}>
                {i + 1}
              </span>
              <span className="rounded-lg bg-white/[0.02] px-3 py-1.5 text-slate-300">
                <span className="mr-2" style={{ color }}>{lvl.toUpperCase()}</span>
                {msg}
              </span>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  )
}