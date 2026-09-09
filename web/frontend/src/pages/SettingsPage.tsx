import { useEffect, useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'

interface Settings {
  llm_provider: 'mock' | 'openai' | 'anthropic'
  default_strategy: string
  confidence_threshold: number
  anomaly_threshold: number
  max_agent_iterations: number
  trace_level: 'system' | 'all'
  memory_consolidation: boolean
  audit_every_scan: boolean
}

const defaults: Settings = {
  llm_provider: 'mock',
  default_strategy: 'deep_scan',
  confidence_threshold: 0.6,
  anomaly_threshold: 0.6,
  max_agent_iterations: 12,
  trace_level: 'all',
  memory_consolidation: true,
  audit_every_scan: true,
}

const providers = [
  { key: 'mock', label: 'Mock Provider', desc: '确定性仿真，离线稳定' },
  { key: 'openai', label: 'OpenAI', desc: 'GPT-4o 系列' },
  { key: 'anthropic', label: 'Anthropic', desc: 'Claude Sonnet 系列' },
] as const

function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!on)}
      className={`relative h-5 w-9 rounded-full transition-colors ${on ? 'bg-[rgba(0,245,255,0.35)]' : 'bg-white/[0.08]'}`}
    >
      <span
        className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${on ? 'left-[18px] shadow-[0_0_8px_rgba(0,245,255,0.8)]' : 'left-0.5'}`}
      />
    </button>
  )
}

export default function SettingsPage() {
  const [s, setS] = useState<Settings>(defaults)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('abd.settings')
      if (raw) setS({ ...defaults, ...JSON.parse(raw) })
    } catch {
      /* ignore */
    }
  }, [])

  const save = () => {
    localStorage.setItem('abd.settings', JSON.stringify(s))
    setSaved(true)
    setTimeout(() => setSaved(false), 1800)
  }

  const update = <K extends keyof Settings>(k: K, v: Settings[K]) => setS((p) => ({ ...p, [k]: v }))

  const inputCls =
    'rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(255,255,255,0.03)] px-3 py-2 font-mono text-[12px] text-slate-200 outline-none focus:border-[rgba(0,245,255,0.4)]'

  return (
    <div className="fade-in mx-auto flex max-w-[900px] flex-col gap-5">
      {/* LLM provider */}
      <GlassCard className="p-0">
        <div className="flex items-center justify-between border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div>
            <h2 className="text-[13px] font-bold text-white">LLM Provider</h2>
            <p className="text-[11px] text-slate-500">Agent 推理与决策引擎后端</p>
          </div>
          <Badge tone="purple">{s.llm_provider.toUpperCase()}</Badge>
        </div>
        <div className="grid grid-cols-3 gap-3 p-5">
          {providers.map((p) => (
            <button
              key={p.key}
              onClick={() => update('llm_provider', p.key)}
              className={`rounded-xl border p-4 text-left transition-all ${
                s.llm_provider === p.key
                  ? 'border-[rgba(139,92,246,0.5)] bg-[rgba(139,92,246,0.08)]'
                  : 'border-[rgba(148,163,184,0.1)] bg-white/[0.02] hover:border-[rgba(148,163,184,0.3)]'
              }`}
            >
              <div className={`text-[13px] font-bold ${s.llm_provider === p.key ? 'text-[#c4b5fd]' : 'text-slate-300'}`}>{p.label}</div>
              <div className="mt-1 text-[11px] text-slate-500">{p.desc}</div>
            </button>
          ))}
        </div>
      </GlassCard>

      {/* detection params */}
      <GlassCard className="p-0">
        <div className="border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <h2 className="text-[13px] font-bold text-white">Detection Parameters</h2>
          <p className="text-[11px] text-slate-500">工作流扫描阈值与策略</p>
        </div>
        <div className="grid grid-cols-2 gap-5 p-5">
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-slate-400">Default Scan Strategy</label>
            <select value={s.default_strategy} onChange={(e) => update('default_strategy', e.target.value)} className={`${inputCls} w-full`}>
              <option value="fast_scan" className="bg-[#0b1020]">fast_scan</option>
              <option value="deep_scan" className="bg-[#0b1020]">deep_scan</option>
              <option value="forensic_scan" className="bg-[#0b1020]">forensic_scan</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-slate-400">Max Agent Iterations</label>
            <input type="number" value={s.max_agent_iterations} onChange={(e) => update('max_agent_iterations', Number(e.target.value))} className={`${inputCls} w-full`} />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-slate-400">Confidence Threshold</label>
            <input type="number" step="0.05" value={s.confidence_threshold} onChange={(e) => update('confidence_threshold', Number(e.target.value))} className={`${inputCls} w-full`} />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-slate-400">Anomaly Threshold</label>
            <input type="number" step="0.05" value={s.anomaly_threshold} onChange={(e) => update('anomaly_threshold', Number(e.target.value))} className={`${inputCls} w-full`} />
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-slate-400">Trace Level</label>
            <select value={s.trace_level} onChange={(e) => update('trace_level', e.target.value as Settings['trace_level'])} className={`${inputCls} w-full`}>
              <option value="system" className="bg-[#0b1020]">system</option>
              <option value="all" className="bg-[#0b1020]">system + data + decision + audit</option>
            </select>
          </div>
        </div>
      </GlassCard>

      {/* runtime toggles */}
      <GlassCard className="p-0">
        <div className="border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <h2 className="text-[13px] font-bold text-white">Runtime Behavior</h2>
        </div>
        <div className="divide-y divide-[rgba(148,163,184,0.06)] px-5">
          {[
            { key: 'memory_consolidation', label: 'Periodic Memory Consolidation', desc: '每 30 分钟将 episodic → semantic 固化' },
            { key: 'audit_every_scan', label: 'Audit Trail on Every Scan', desc: '每次扫描生成不可篡改审计记录' },
          ].map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between py-3.5">
              <div>
                <div className="text-[13px] text-slate-200">{label}</div>
                <div className="text-[11px] text-slate-500">{desc}</div>
              </div>
              <Toggle on={s[key as keyof Settings] as boolean} onChange={(v) => update(key as keyof Settings, v)} />
            </div>
          ))}
        </div>
      </GlassCard>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          className="rounded-xl border border-[rgba(0,245,255,0.4)] bg-[rgba(0,245,255,0.1)] px-6 py-2.5 text-[12px] font-semibold text-[#00f5ff] transition-all hover:bg-[rgba(0,245,255,0.18)]"
        >
          Save Configuration
        </button>
        <button
          onClick={() => setS(defaults)}
          className="rounded-xl border border-[rgba(148,163,184,0.15)] px-6 py-2.5 text-[12px] font-semibold text-slate-400 transition-colors hover:text-slate-200"
        >
          Reset Defaults
        </button>
        {saved && <Badge tone="green" pulse>CONFIG SAVED</Badge>}
      </div>
    </div>
  )
}