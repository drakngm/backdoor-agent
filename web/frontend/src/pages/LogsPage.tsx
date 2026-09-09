import { useEffect, useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import { api } from '../api/client'
import type { LogEntry } from '../types'

const levelTone: Record<LogEntry['level'], string> = {
  INFO: 'text-[#7dd3fc]',
  WARN: 'text-[#f59e0b]',
  ERROR: 'text-[#ef4444]',
  DEBUG: 'text-[#94a3b8]',
  TRACE: 'text-[#22c55e]',
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [filter, setFilter] = useState<'all' | LogEntry['level']>('all')

  useEffect(() => {
    api.logs().then(setLogs)
    const t = setInterval(() => {
      api.logs().then(setLogs)
    }, 8000)
    return () => clearInterval(t)
  }, [])

  const shown = filter === 'all' ? logs : logs.filter((l) => l.level === filter)

  return (
    <div className="fade-in mx-auto flex max-w-[1000px] flex-col gap-5">
      <GlassCard className="p-0">
        <div className="flex flex-wrap items-center gap-2 border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div className="mr-2">
            <h2 className="text-[13px] font-bold text-white">System Logs</h2>
            <p className="text-[11px] text-slate-500">HTTP · Core · Agent · Tool runtime</p>
          </div>
          <div className="ml-auto flex items-center gap-1">
            {(['all', 'INFO', 'DEBUG', 'WARN', 'ERROR'] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setFilter(lvl)}
                className={`rounded-lg px-2.5 py-1 text-[10px] font-medium transition-colors ${
                  filter === lvl ? 'bg-[rgba(0,245,255,0.1)] text-[#00f5ff]' : 'text-slate-500 hover:text-slate-200'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
        <div className="h-[560px] overflow-y-auto p-4">
          <div className="space-y-1 font-mono text-[11px] leading-relaxed">
            {shown.map((l, i) => (
              <div key={i} className={`flex items-start gap-3 rounded-lg px-3 py-1.5 transition-colors ${l.level === 'ERROR' ? 'bg-[rgba(239,68,68,0.05)]' : 'hover:bg-white/[0.02]'}`}>
                <span className="digits w-[86px] shrink-0 text-slate-600">
                  {new Date(l.time).toLocaleTimeString('zh-CN', { hour12: false, fractionalSecondDigits: 3 })}
                </span>
                <span className={`w-[52px] shrink-0 font-bold ${levelTone[l.level]}`}>{l.level}</span>
                <span className="w-[150px] shrink-0 truncate text-slate-500">{l.logger}</span>
                <span className="min-w-0 flex-1 text-slate-300">{l.message}</span>
                {l.trace_id && <span className="ml-auto shrink-0 text-[10px] text-slate-600">{l.trace_id}</span>}
              </div>
            ))}
          </div>
        </div>
      </GlassCard>
    </div>
  )
}