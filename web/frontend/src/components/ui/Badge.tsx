import type { ReactNode } from 'react'

export type BadgeTone = 'cyan' | 'blue' | 'purple' | 'green' | 'amber' | 'red' | 'gray'

const tones: Record<BadgeTone, string> = {
  cyan: 'text-[#00f5ff] bg-[rgba(0,245,255,0.08)] border-[rgba(0,245,255,0.3)]',
  blue: 'text-[#3b82f6] bg-[rgba(59,130,246,0.08)] border-[rgba(59,130,246,0.3)]',
  purple: 'text-[#8b5cf6] bg-[rgba(139,92,246,0.08)] border-[rgba(139,92,246,0.3)]',
  green: 'text-[#22c55e] bg-[rgba(34,197,94,0.08)] border-[rgba(34,197,94,0.3)]',
  amber: 'text-[#f59e0b] bg-[rgba(245,158,11,0.08)] border-[rgba(245,158,11,0.3)]',
  red: 'text-[#ef4444] bg-[rgba(239,68,68,0.08)] border-[rgba(239,68,68,0.3)]',
  gray: 'text-[#94a3b8] bg-[rgba(148,163,184,0.06)] border-[rgba(148,163,184,0.15)]',
}

interface BadgeProps {
  tone?: BadgeTone
  children: ReactNode
  pulse?: boolean
  className?: string
}

export default function Badge({ tone = 'gray', children, pulse, className = '' }: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wider uppercase',
        tones[tone],
        className,
      ].join(' ')}
    >
      {pulse && (
        <span className={`h-1.5 w-1.5 rounded-full ${tone === 'gray' ? 'bg-current opacity-60' : ''}`}>
          <span className="dot-pulse block h-full w-full rounded-full bg-current" />
        </span>
      )}
      {children}
    </span>
  )
}