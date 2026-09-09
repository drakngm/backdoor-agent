import type { ReactNode } from 'react'
import type { BadgeTone } from './Badge'

interface MetricProps {
  label: string
  value: ReactNode
  unit?: string
  tone?: BadgeTone
  sub?: ReactNode
  delta?: string
  glow?: boolean
}

const tones: Record<BadgeTone, string> = {
  cyan: 'text-[#00f5ff]',
  blue: 'text-[#3b82f6]',
  purple: 'text-[#8b5cf6]',
  green: 'text-[#22c55e]',
  amber: 'text-[#f59e0b]',
  red: 'text-[#ef4444]',
  gray: 'text-[#e2e8f0]',
}

export default function Metric({ label, value, unit, tone = 'cyan', sub, delta }: MetricProps) {
  return (
    <div className="flex min-w-0 flex-col justify-center">
      <div className="flex items-center gap-2">
        <span className={`digits text-2xl font-semibold tracking-tight leading-none ${tones[tone]}`}>{value}</span>
        {unit && <span className="digits text-xs text-slate-400">{unit}</span>}
        {delta && (
          <span className={`digits text-[10px] ${delta.startsWith('+') || delta.startsWith('↑') ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
            {delta}
          </span>
        )}
      </div>
      <div className="mt-1 truncate text-[11px] font-medium tracking-wider text-slate-400 uppercase">{label}</div>
      {sub && <div className="mt-0.5 text-[10px] text-slate-500">{sub}</div>}
    </div>
  )
}