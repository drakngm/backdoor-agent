import { useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function StatusBar() {
  const [latency, setLatency] = useState(0)
  const [traceId, setTraceId] = useState('trc_9f2a11c4')

  useEffect(() => {
    api.resources().then((r) => setLatency(Math.round(80 + r.gpu * 1.4)))
    const t = setInterval(() => {
      setLatency(Math.round(60 + Math.random() * 120))
      setTraceId(() => {
        const chars = '0123456789abcdef'
        return 'trc_' + Array.from({ length: 8 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
      })
    }, 4000)
    return () => clearInterval(t)
  }, [])

  return (
    <footer className="flex h-[32px] items-center gap-5 border-t border-[rgba(148,163,184,0.08)] bg-[#05070a]/70 px-5 text-[10px] text-slate-500 backdrop-blur">
      <span className="flex items-center gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-[#22c55e] dot-pulse" />
        <span className="font-semibold tracking-wider text-slate-300 uppercase">Core Engine</span>
        <span className="font-mono text-[#00f5ff]/80">v1.4.0</span>
      </span>
      <span className="h-3 w-px bg-[rgba(148,163,184,0.15)]" />
      <span className="flex items-center gap-1.5">
        <span className="tracking-wider uppercase">Latency</span>
        <span className="digits text-slate-300">{latency} ms</span>
      </span>
      <span className="hidden h-3 w-px bg-[rgba(148,163,184,0.15)] md:block" />
      <span className="hidden items-center gap-1.5 md:flex">
        <span className="tracking-wider uppercase">Active Trace</span>
        <span className="font-mono text-slate-300">{traceId}</span>
      </span>
      <span className="ml-auto flex items-center gap-2">
        <span className="flex items-center gap-1">
          <span className="h-1 w-1 rounded-full bg-[#22c55e]" />
          <span className="tracking-wider uppercase">4 LVL Trace</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="h-1 w-1 rounded-full bg-[#8b5cf6]" />
          <span className="tracking-wider uppercase">DAG Orchestration</span>
        </span>
        <span className="font-mono text-slate-600">/* federation-node-07 */</span>
      </span>
    </footer>
  )
}