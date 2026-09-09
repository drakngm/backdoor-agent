import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import type { ThreatItem, SystemResource } from '../../types'

const sevTone = {
  critical: 'text-[#ef4444] border-[rgba(239,68,68,0.3)] bg-[rgba(239,68,68,0.08)]',
  high: 'text-[#f59e0b] border-[rgba(245,158,11,0.3)] bg-[rgba(245,158,11,0.08)]',
  medium: 'text-[#3b82f6] border-[rgba(59,130,246,0.3)] bg-[rgba(59,130,246,0.08)]',
  low: 'text-[#22c55e] border-[rgba(34,197,94,0.3)] bg-[rgba(34,197,94,0.08)]',
}

function ResourceBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium tracking-wider text-slate-400 uppercase">{label}</span>
        <span className="digits text-[10px] text-slate-300">{Math.round(value)}%</span>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${Math.min(100, value)}%`, boxShadow: `0 0 8px ${color === 'bg-[#00f5ff]/70' ? 'rgba(0,245,255,0.6)' : 'rgba(139,92,246,0.6)'}` }}
        />
      </div>
    </div>
  )
}

export default function RightPanel() {
  const [threats, setThreats] = useState<ThreatItem[]>([])
  const [res, setRes] = useState<SystemResource>({ cpu: 0, gpu: 0, mem: 0, gpu_name: '—' })

  useEffect(() => {
    api.threats().then(setThreats)
    api.resources().then(setRes)
    const t = setInterval(() => api.resources().then(setRes), 4000)
    return () => clearInterval(t)
  }, [])

  return (
    <aside className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      {/* System resources */}
      <section className="glass p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[11px] font-bold tracking-[0.14em] text-slate-300 uppercase">System Resources</h3>
          <span className="text-[9px] text-slate-500 dot-pulse">LIVE</span>
        </div>
        <div className="mb-3 rounded-lg bg-[rgba(255,255,255,0.02)] px-2.5 py-2 font-mono text-[10px] text-[#8b5cf6]">{res.gpu_name}</div>
        <div className="space-y-3">
          <ResourceBar label="GPU" value={res.gpu} color="bg-[#00f5ff]/70" />
          <ResourceBar label="CPU" value={res.cpu} color="bg-[#8b5cf6]/70" />
          <ResourceBar label="MEM" value={res.mem} color="bg-[#3b82f6]/70" />
        </div>
      </section>

      {/* Threat intelligence */}
      <section className="glass p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[11px] font-bold tracking-[0.14em] text-slate-300 uppercase">Threat Intel</h3>
          <span className="rounded-full border border-[rgba(148,163,184,0.15)] px-2 py-0.5 text-[9px] text-slate-400">
            {threats.length} events
          </span>
        </div>
        <div className="space-y-2.5">
          {threats.length === 0 && (
            <div className="flex h-20 items-center justify-center text-[11px] text-slate-600">Awaiting telemetry…</div>
          )}
          {threats.map((t) => (
            <div key={t.id} className="rounded-xl border border-[rgba(148,163,184,0.08)] bg-white/[0.02] p-3 transition-colors hover:border-[rgba(0,245,255,0.2)]">
              <div className="flex items-center justify-between">
                <span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold tracking-wider uppercase ${sevTone[t.severity]}`}>
                  {t.severity}
                </span>
                <span className="font-mono text-[9px] text-slate-600">{t.id}</span>
              </div>
              <div className="mt-2 flex items-center gap-1.5 text-[11px] font-medium text-slate-300">
                <svg viewBox="0 0 24 24" className="h-3 w-3 shrink-0 text-[#00f5ff]" {...stroke}>
                  <path d="M13 2 L4.5 13 H11 L9.5 22 L19.5 9.5 H12.5 Z" />
                </svg>
                <span className="truncate font-mono text-[10px] text-slate-400">{t.source}</span>
              </div>
              <p className="mt-1.5 text-[11px] leading-relaxed text-slate-300">{t.summary}</p>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[9px] text-slate-500">{t.detector}</span>
                <span className="font-mono text-[9px] text-slate-600">{new Date(t.time).toLocaleTimeString('zh-CN', { hour12: false })}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Decision stream */}
      <section className="glass p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-[11px] font-bold tracking-[0.14em] text-slate-300 uppercase">LLM Decision Stream</h3>
          <span className="text-[9px] text-slate-500">CoT</span>
        </div>
        <div className="space-y-2 rounded-xl bg-[rgba(5,7,10,0.6)] p-3 font-mono text-[10px] leading-relaxed text-[#7dd3fc]">
          <p><span className="text-[#8b5cf6]">›</span> 解析模型结构 @conv4_2，可疑触发敏感区</p>
          <p><span className="text-[#8b5cf6]">›</span> 调度 STRIP → 请求工具适配器</p>
          <p><span className="text-[#22c55e]">✓</span> STRIP 通过 · 置信度 0.93</p>
          <p><span className="text-[#f59e0b]">⚠</span> 触发逆向异常分数 0.87 &gt; 0.6</p>
          <p><span className="text-[#8b5cf6]">›</span> 提升深度扫描 → 交叉验证</p>
          <span className="caret inline-block h-3 w-1.5 bg-[#00f5ff]/70 align-middle" />
        </div>
      </section>
    </aside>
  )
}

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}