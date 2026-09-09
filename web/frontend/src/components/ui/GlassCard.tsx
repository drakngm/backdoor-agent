import type { ReactNode } from 'react'

interface GlassCardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  glow?: boolean
  pad?: 'none' | 'sm' | 'md' | 'lg'
}

export default function GlassCard({ children, className = '', hover, glow, pad = 'md' }: GlassCardProps) {
  const pads = { none: 'p-0', sm: 'p-3', md: 'p-5', lg: 'p-6' }
  return (
    <div
      className={[
        'glass',
        pads[pad],
        hover && 'transition-all duration-300 hover:-translate-y-0.5 hover:border-white/15 hover:shadow-[0_16px_40px_-16px_rgba(0,0,0,0.9)]',
        glow && 'glow-cyan',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}