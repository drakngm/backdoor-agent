import { NavLink } from 'react-router-dom'

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
}

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.4,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

const Icons = {
  overview: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  ),
  agent: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <path d="M12 3 L21 7.5 V16.5 L12 21 L3 16.5 V7.5 Z" />
      <circle cx="12" cy="12" r="2.6" />
      <path d="M12 6 V 9.4 M12 14.6 V 18 M6 12 H 9.4 M14.6 12 H 18" />
    </svg>
  ),
  hybrid: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="12" cy="18" r="3" />
      <path d="M9 7.2 L10.8 15 M15 7.2 L13.2 15" />
    </svg>
  ),
  workflow: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <rect x="3" y="3" width="6" height="6" rx="1.2" />
      <rect x="15" y="15" width="6" height="6" rx="1.2" />
      <path d="M9 6 H14 a3 3 0 0 1 3 3 v6 M6 9 v6 a3 3 0 0 0 3 3 h6" />
    </svg>
  ),
  shield: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <path d="M12 3 L20 6 V12 C20 17 16.5 20.5 12 22 C7.5 20.5 4 17 4 12 V6 Z" />
      <path d="M8.5 12 l2.4 2.4 4.6-4.6" />
    </svg>
  ),
  memory: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M8 8 v8 M12 8 v8 M16 8 v8 M3 12 h18" />
    </svg>
  ),
  trace: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <path d="M4 6 h16 M4 12 h10 M4 18 h14" />
      <circle cx="20" cy="6" r="1.5" />
      <circle cx="17" cy="12" r="1.5" />
      <circle cx="21" cy="18" r="1.5" />
    </svg>
  ),
  logs: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <path d="M5 4 h14 M5 9 h14 M5 14 h9" />
      <path d="M5 19 h6 M6 16 l3 3 -3 3" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" {...stroke}>
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 3.5 v3 M12 17.5 v3 M3.5 12 h3 M17.5 12 h3 M6 6 l2.1 2.1 M15.9 15.9 l2.1 2.1 M18 6 l-2.1 2.1 M8.1 15.9 L6 18" />
    </svg>
  ),
}

const navItems: NavItem[] = [
  { to: '/', label: 'Overview', icon: Icons.overview },
  { to: '/agent', label: 'Agent Console', icon: Icons.agent },
  { to: '/hybrid', label: 'Hybrid Agent', icon: Icons.hybrid },
  { to: '/workflow', label: 'Workflow', icon: Icons.workflow },
  { to: '/detection', label: 'Backdoor Detection', icon: Icons.shield },
  { to: '/memory', label: 'Memory', icon: Icons.memory },
  { to: '/trace', label: 'Trace & Audit', icon: Icons.trace },
  { to: '/logs', label: 'Logs', icon: Icons.logs },
  { to: '/settings', label: 'Settings', icon: Icons.settings },
]

export default function Sidebar() {
  return (
    <aside className="flex h-full flex-col border-r border-[rgba(148,163,184,0.08)] bg-[#05070a]/70 backdrop-blur-xl">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 pt-5 pb-4">
        <div className="relative">
          <svg viewBox="0 0 32 32" className="h-9 w-9">
            <defs>
              <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#00f5ff" />
                <stop offset="1" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>
            <rect width="32" height="32" rx="8" fill="rgba(0,245,255,0.06)" stroke="rgba(0,245,255,0.25)" />
            <path d="M16 7 L25.5 25 H6.5 Z" fill="none" stroke="url(#lg)" strokeWidth="1.6" />
            <circle cx="16" cy="16.5" r="3.6" fill="url(#lg)" />
          </svg>
          <span className="absolute -right-0.5 -bottom-0.5 h-2.5 w-2.5 rounded-full bg-[#22c55e] dot-pulse" />
        </div>
        <div className="leading-tight">
          <div className="font-display text-[13px] font-bold tracking-wide text-white">AI Backdoor Defense</div>
          <div className="text-[10px] tracking-[0.2em] text-slate-500 uppercase">Command Center</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="mt-2 flex-1 space-y-0.5 overflow-y-auto px-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              [
                'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-200',
                isActive
                  ? 'bg-[rgba(0,245,255,0.07)] text-[#00f5ff] shadow-[inset_0_0_0_1px_rgba(0,245,255,0.15)]'
                  : 'text-slate-400 hover:bg-white/[0.03] hover:text-slate-100',
              ].join(' ')
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded-full bg-[#00f5ff] shadow-[0_0_10px_rgba(0,245,255,0.9)]" />
                )}
                <span className={isActive ? 'text-[#00f5ff] drop-shadow-[0_0_6px_rgba(0,245,255,0.6)]' : 'text-slate-500 group-hover:text-slate-300'}>
                  {item.icon}
                </span>
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Profile */}
      <div className="border-t border-[rgba(148,163,184,0.08)] p-4">
        <div className="flex items-center gap-3">
          <div className="relative h-9 w-9 rounded-xl bg-gradient-to-tr from-[#3b82f6]/30 to-[#8b5cf6]/30 ring-1 ring-[rgba(148,163,184,0.2)]">
            <span className="flex h-full w-full items-center justify-center text-[11px] font-semibold text-cyan-200">OP</span>
            <span className="absolute -right-0.5 -bottom-0.5 h-2.5 w-2.5 rounded-full border border-[#05070a] bg-[#22c55e] dot-pulse" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[12px] font-semibold text-white">Soc Operator</div>
            <div className="text-[10px] text-slate-500">ai-security@federation</div>
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between rounded-lg bg-[rgba(0,245,255,0.05)] px-2.5 py-1.5 ring-1 ring-[rgba(0,245,255,0.12)]">
          <span className="text-[9px] font-bold tracking-[0.18em] text-[#00f5ff] uppercase">Env</span>
          <span className="text-[9px] font-semibold tracking-wider text-amber-300">PRODUCTION</span>
        </div>
      </div>
    </aside>
  )
}