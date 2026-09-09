import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../../api/client'
import type { Env } from '../../types'

const pageNames: Record<string, string> = {
  '/': 'Command Center',
  '/agent': 'Agent Console',
  '/hybrid': 'Hybrid Agent',
  '/workflow': 'Workflow',
  '/detection': 'Backdoor Detection',
  '/memory': 'Memory',
  '/trace': 'Trace & Audit',
  '/logs': 'Logs',
  '/settings': 'Settings',
}

const envs: Env[] = ['PRODUCTION', 'STAGING', 'DEVELOPMENT']

export default function TopHeader() {
  const { pathname } = useLocation()
  const [clock, setClock] = useState(new Date())
  const [connected, setConnected] = useState(true)
  const [env, setEnv] = useState<Env>('PRODUCTION')
  const [showEnv, setShowEnv] = useState(false)

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    let alive = true
    const poll = async () => {
      const h = await api.health()
      if (alive) setConnected(h.status !== 'down' || (h.backend_connected ?? true))
    }
    poll()
    const t = setInterval(poll, 15000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  const page = pageNames[pathname] ?? 'Command Center'

  return (
    <header className="relative z-20 flex h-[72px] items-center gap-6 border-b border-[rgba(148,163,184,0.08)] bg-[#05070a]/60 px-6 backdrop-blur-xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-[12px]">
        <span className="text-slate-500">Overview</span>
        <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-slate-600" {...stroke}>
          <path d="M9 6 l6 6 -6 6" />
        </svg>
        <span className="font-semibold text-slate-200">{page}</span>
      </div>

      {/* Search */}
      <div className="relative mx-auto w-full max-w-md">
        <svg viewBox="0 0 24 24" className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" {...stroke}>
          <circle cx="11" cy="11" r="7" />
          <path d="M21 21 l-4.35-4.35" />
        </svg>
        <input
          placeholder="Search models, threats, hashes, workflows..."
          className="w-full rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] py-2 pl-10 pr-4 text-[13px] text-slate-200 outline-none transition-all placeholder:text-slate-600 focus:border-[rgba(0,245,255,0.4)] focus:bg-[rgba(0,245,255,0.03)] focus:shadow-[0_0_0_3px_rgba(0,245,255,0.08)]"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-[rgba(148,163,184,0.15)] bg-[rgba(255,255,255,0.04)] px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
          ⌘K
        </kbd>
      </div>

      {/* Right cluster */}
      <div className="flex items-center gap-3">
        {/* Env selector */}
        <div className="relative">
          <button
            onClick={() => setShowEnv((s) => !s)}
            className="flex items-center gap-2 rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] px-3 py-1.5 text-[11px] font-semibold transition-colors hover:border-[rgba(0,245,255,0.3)]"
          >
            <span className={`h-1.5 w-1.5 rounded-full ${env === 'PRODUCTION' ? 'bg-amber-300' : env === 'STAGING' ? 'bg-[#3b82f6]' : 'bg-[#22c55e]'}`} />
            <span className="text-slate-200">{env}</span>
            <svg viewBox="0 0 24 24" className="h-3 w-3 text-slate-500" {...stroke}>
              <path d="M6 9 l6 6 6-6" />
            </svg>
          </button>
          {showEnv && (
            <div className="glass fade-in absolute right-0 top-12 z-30 w-36 p-1 shadow-[0_16px_40px_-12px_rgba(0,0,0,0.9)]">
              {envs.map((e) => (
                <button
                  key={e}
                  onClick={() => {
                    setEnv(e)
                    setShowEnv(false)
                  }}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-[12px] transition-colors ${e === env ? 'bg-[rgba(0,245,255,0.08)] text-[#00f5ff]' : 'text-slate-400 hover:bg-white/[0.03] hover:text-slate-200'}`}
                >
                  {e}
                  {e === env && <span className="text-[#00f5ff]">●</span>}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notifications */}
        <button className="relative rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] p-2 transition-colors hover:border-[rgba(0,245,255,0.3)]">
          <svg viewBox="0 0 24 24" className="h-4 w-4 text-slate-300" {...stroke}>
            <path d="M18 9 a6 6 0 0 0 -12 0 c0 7 -3 8 -3 8 h18 c0 0 -3 -1 -3 -8" />
            <path d="M13.7 20 a2 2 0 0 1 -3.4 0" />
          </svg>
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-[#ef4444] ring-2 ring-[#05070a]" />
        </button>

        {/* Clock */}
        <div className="hidden flex-col items-end leading-tight md:flex">
          <div className="digits text-[13px] font-semibold text-slate-200">
            {clock.toLocaleTimeString('zh-CN', { hour12: false })}
          </div>
          <div className="text-[10px] text-slate-500">
            {clock.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', weekday: 'short' })}
          </div>
        </div>

        {/* Connection */}
        <div className="flex items-center gap-2 rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] px-3 py-2">
          <span className={`flex items-center gap-1 text-[10px] font-semibold ${connected ? 'text-[#22c55e]' : 'text-amber-300'}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-[#22c55e] dot-pulse' : 'bg-amber-300'}`} />
            {connected ? 'ONLINE' : 'DEGRADED'}
          </span>
        </div>

        {/* Avatar */}
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-[#3b82f6]/30 to-[#8b5cf6]/30 text-[10px] font-bold text-white ring-1 ring-[rgba(148,163,184,0.2)]">
          OP
        </div>
      </div>
    </header>
  )
}

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}