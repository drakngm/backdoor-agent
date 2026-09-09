import { useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'
import { api } from '../api/client'
import type { ExecuteResult } from '../types'

const strategies = [
  { key: 'fast_scan', label: 'Fast Scan', desc: '单工具 STRIP 快速筛查，<500ms 响应', tone: 'cyan' as const, color: '#00f5ff' },
  { key: 'deep_scan', label: 'Deep Scan', desc: 'STRIP + Neural Cleanse 双检，触发逆向分析', tone: 'blue' as const, color: '#3b82f6' },
  { key: 'forensic_scan', label: 'Forensic Scan', desc: '三检测器全量交叉验证，生成审计报告', tone: 'purple' as const, color: '#8b5cf6' },
]

export default function WorkflowPage() {
  const [strategy, setStrategy] = useState('deep_scan')
  const [modelPath, setModelPath] = useState('model.h5')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<ExecuteResult | null>(null)

  const run = async () => {
    if (running) return
    setRunning(true)
    setResult(null)
    try {
      const res = await api.execute('workflow', { strategy, model_path: modelPath })
      setResult(res)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="fade-in mx-auto flex max-w-[1000px] flex-col gap-5">
      {/* strategy cards */}
      <div className="grid grid-cols-3 gap-5">
        {strategies.map((s) => (
          <button
            key={s.key}
            onClick={() => setStrategy(s.key)}
            className={`glass p-4 text-left transition-all duration-200 ${strategy === s.key ? 'glow-cyan' : 'opacity-70 hover:opacity-100'}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-display text-[14px] font-bold text-white">{s.label}</span>
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ background: strategy === s.key ? s.color : 'rgba(148,163,184,0.3)', boxShadow: strategy === s.key ? `0 0 10px ${s.color}` : 'none' }}
              />
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{s.desc}</p>
            <span className="mt-3 inline-block font-mono text-[10px] text-[#7dd3fc]">{s.key}</span>
          </button>
        ))}
      </div>

      {/* runner */}
      <GlassCard className="p-0">
        <div className="flex items-center justify-between border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div>
            <h2 className="text-[13px] font-bold text-white">Workflow Executor</h2>
            <p className="text-[11px] text-slate-500">Planner → Task Graph DAG → Executor</p>
          </div>
          <Badge tone={running ? 'cyan' : 'gray'} pulse={running}>{running ? 'RUNNING' : 'IDLE'}</Badge>
        </div>
        <div className="flex gap-3 p-5">
          <input
            value={modelPath}
            onChange={(e) => setModelPath(e.target.value)}
            placeholder="model_path"
            className="flex-1 rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] px-4 py-2.5 font-mono text-[12px] text-slate-200 outline-none focus:border-[rgba(0,245,255,0.4)]"
          />
          <button
            onClick={run}
            disabled={running}
            className="rounded-xl border border-[rgba(0,245,255,0.4)] bg-[rgba(0,245,255,0.1)] px-6 text-[12px] font-semibold text-[#00f5ff] transition-all hover:bg-[rgba(0,245,255,0.18)] disabled:opacity-40"
          >
            {running ? 'Executing DAG…' : 'Run Workflow'}
          </button>
        </div>
      </GlassCard>

      {result && (
        <GlassCard>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge tone="blue">{result.strategy ?? 'workflow'}</Badge>
            <Badge tone={result.status === 'completed' ? 'green' : 'amber'}>{result.status}</Badge>
            <span className="font-mono text-[10px] text-slate-500">{result.trace_id}</span>
            {result.source === 'mock' && <Badge tone="gray">MOCK FALLBACK</Badge>}
          </div>
          {result.final_answer && (
            <div className="glass-inner mb-4 p-4">
              <div className="mb-2 text-[10px] font-bold tracking-wider text-[#00f5ff] uppercase">Execution Report</div>
              <p className="text-[13px] leading-relaxed text-slate-200">{result.final_answer}</p>
            </div>
          )}
          {result.critical_path && (
            <div className="mb-3">
              <div className="mb-1.5 text-[10px] font-bold tracking-wider text-slate-500 uppercase">Executed Path</div>
              <div className="flex flex-wrap items-center gap-1.5">
                {result.critical_path.map((s, i) => (
                  <span key={i} className="flex items-center gap-1.5">
                    <span className="rounded-md border border-[rgba(148,163,184,0.15)] bg-white/[0.02] px-2 py-1 font-mono text-[10px] text-slate-300">{s}</span>
                    {i < result.critical_path!.length - 1 && <span className="text-[#00f5ff]/60">→</span>}
                  </span>
                ))}
              </div>
            </div>
          )}
        </GlassCard>
      )}
    </div>
  )
}