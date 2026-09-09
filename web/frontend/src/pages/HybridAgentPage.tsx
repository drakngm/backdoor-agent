import { useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'
import { api } from '../api/client'
import type { ExecuteResult } from '../types'

const verdictTone: Record<string, { tone: 'green' | 'amber' | 'red'; label: string }> = {
  CLEAN: { tone: 'green', label: '模型安全' },
  SUSPICIOUS: { tone: 'amber', label: '存在可疑特征' },
  BACKDOOR: { tone: 'red', label: '检测到后门' },
}

export default function HybridAgentPage() {
  const [task, setTask] = useState('对 model.h5 执行深度后门检测')
  const [modelPath, setModelPath] = useState('model.h5')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<ExecuteResult | null>(null)

  const run = async () => {
    if (!task.trim() || running) return
    setRunning(true)
    setResult(null)
    try {
      const res = await api.execute('hybrid', { message: task, model_path: modelPath })
      setResult(res)
    } finally {
      setRunning(false)
    }
  }

  const vt = result && result.verdict ? verdictTone[result.verdict] : null

  return (
    <div className="fade-in mx-auto flex max-w-[1000px] flex-col gap-5">
      <GlassCard className="p-0">
        <div className="flex items-center justify-between border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div>
            <h2 className="text-[13px] font-bold text-white">Hybrid Agent</h2>
            <p className="text-[11px] text-slate-500">模型分析 → 决策引擎 → 编译器 → 执行器</p>
          </div>
          <Badge tone={running ? 'purple' : 'gray'} pulse={running}>{running ? 'RUNNING' : 'READY'}</Badge>
        </div>
        <div className="grid grid-cols-4 gap-3 p-5">
          <input
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Task description…"
            className="col-span-2 rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] px-4 py-2.5 text-[13px] text-slate-200 outline-none focus:border-[rgba(139,92,246,0.4)]"
          />
          <input
            value={modelPath}
            onChange={(e) => setModelPath(e.target.value)}
            placeholder="model_path"
            className="rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] px-4 py-2.5 font-mono text-[12px] text-slate-200 outline-none focus:border-[rgba(139,92,246,0.4)]"
          />
          <button
            onClick={run}
            disabled={running}
            className="rounded-xl border border-[rgba(139,92,246,0.4)] bg-[rgba(139,92,246,0.12)] text-[12px] font-semibold text-[#c4b5fd] transition-all hover:bg-[rgba(139,92,246,0.2)] disabled:opacity-40"
          >
            {running ? 'Analyzing…' : 'Run Hybrid'}
          </button>
        </div>
      </GlassCard>

      {result && vt && result.confidence !== undefined && (
        <>
          {/* Verdict */}
          <GlassCard className={`relative overflow-hidden border !border-[rgba(0,0,0,0)] ${vt.tone === 'green' ? '!bg-[rgba(34,197,94,0.05)]' : vt.tone === 'amber' ? '!bg-[rgba(245,158,11,0.05)]' : '!bg-[rgba(239,68,68,0.07)]'}`}>
            <div className="flex items-center justify-between gap-5">
              <div>
                <div className="text-[10px] font-bold tracking-[0.25em] text-slate-400 uppercase">Final Verdict</div>
                <div className={`mt-1 font-display text-3xl font-bold ${vt.tone === 'green' ? 'text-[#22c55e]' : vt.tone === 'amber' ? 'text-[#f59e0b]' : 'text-[#ef4444]'} text-glow-cyan`}>
                  {result.verdict}
                </div>
                <div className="mt-1 text-[12px] text-slate-400">{vt.label}</div>
              </div>
              <div className="flex flex-col items-center">
                <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Confidence</div>
                <div className="digits text-4xl font-bold text-[#00f5ff]" style={{ textShadow: '0 0 24px rgba(0,245,255,0.5)' }}>
                  {result.confidence}%
                </div>
                <div className="mt-2 h-1.5 w-40 overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className={`h-full rounded-full ${result.confidence > 50 ? 'bg-[#ef4444]' : 'bg-[#22c55e]'}`}
                    style={{ width: `${result.confidence}%`, boxShadow: '0 0 12px rgba(0,245,255,0.5)' }}
                  />
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Decisions */}
          <GlassCard>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-[11px] font-bold tracking-[0.14em] text-slate-300 uppercase">Decision Chain</h3>
              <Badge tone="purple">Agent Loop</Badge>
            </div>
            <div className="space-y-2">
              {(result.decisions ?? []).map((d, i) => (
                <div key={i} className="flex items-start gap-3 rounded-xl bg-white/[0.02] px-3 py-2.5">
                  <span className="digits mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-[rgba(139,92,246,0.15)] text-[10px] font-bold text-[#c4b5fd]">{i + 1}</span>
                  <p className="text-[12px] leading-relaxed text-slate-300">{d}</p>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Tool results */}
          <GlassCard>
            <h3 className="mb-3 text-[11px] font-bold tracking-[0.14em] text-slate-300 uppercase">Tool Execution</h3>
            <div className="grid grid-cols-3 gap-3">
              {(result.tool_results ?? []).map((t, i) => (
                <div key={i} className="rounded-xl border border-[rgba(148,163,184,0.1)] bg-white/[0.02] p-3.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-semibold text-slate-200">{String(t.tool)}</span>
                    <span className={`h-2 w-2 rounded-full ${t.passed ? 'bg-[#22c55e]' : 'bg-[#ef4444]'} ${t.passed ? '' : 'animate-pulse'}`} />
                  </div>
                  <div className="mt-1.5 text-[10px] text-slate-500">
                    {String(t.done)} · {t.passed ? 'passed' : 'flagged'}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </>
      )}
    </div>
  )
}