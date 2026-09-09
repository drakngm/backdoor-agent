import { useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'
import { api } from '../api/client'
import type { ExecuteResult } from '../types'

export default function AgentConsolePage() {
  const [message, setMessage] = useState('请检测模型是否包含后门')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<ExecuteResult | null>(null)

  const run = async () => {
    if (!message.trim() || running) return
    setRunning(true)
    setResult(null)
    try {
      const res = await api.execute('agent', { message })
      setResult(res)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="fade-in mx-auto flex max-w-[1000px] flex-col gap-5">
      <GlassCard className="p-0">
        <div className="flex items-center justify-between border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div>
            <h2 className="text-[13px] font-bold text-white">Agent Console</h2>
            <p className="text-[11px] text-slate-500">Agent Loop · LLM → Tool Router → Observation</p>
          </div>
          <Badge tone={running ? 'cyan' : 'gray'} pulse={running}>{running ? 'RUNNING' : 'IDLE'}</Badge>
        </div>
        <div className="flex gap-3 p-5">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && run()}
            placeholder="Describe the detection task…"
            className="flex-1 rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] px-4 py-2.5 text-[13px] text-slate-200 outline-none focus:border-[rgba(0,245,255,0.4)]"
          />
          <button
            onClick={run}
            disabled={running}
            className="rounded-xl border border-[rgba(0,245,255,0.4)] bg-[rgba(0,245,255,0.1)] px-5 text-[12px] font-semibold text-[#00f5ff] transition-all hover:bg-[rgba(0,245,255,0.18)] disabled:opacity-40"
          >
            {running ? 'Executing…' : 'Run Agent'}
          </button>
        </div>
      </GlassCard>

      {result && (
        <GlassCard>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge tone="cyan">{result.mode.toUpperCase()}</Badge>
            <Badge tone={result.status === 'completed' ? 'green' : 'amber'}>{result.status}</Badge>
            <span className="font-mono text-[10px] text-slate-500">{result.trace_id}</span>
            {result.source === 'mock' && <Badge tone="gray">MOCK FALLBACK</Badge>}
          </div>
          {result.final_answer && (
            <div className="glass-inner mb-4 p-4">
              <div className="mb-2 text-[10px] font-bold tracking-wider text-[#00f5ff] uppercase">Final Answer</div>
              <p className="text-[13px] leading-relaxed text-slate-200">{result.final_answer}</p>
            </div>
          )}
          {result.critical_path && (
            <div className="mb-3">
              <div className="mb-1.5 text-[10px] font-bold tracking-wider text-slate-500 uppercase">Critical Path</div>
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