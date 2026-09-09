import { useEffect, useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'
import { api } from '../api/client'
import type { MemorySummary } from '../types'

type LayerKey = 'episodic' | 'semantic' | 'procedural'

const layers: { key: LayerKey; label: string; desc: string; color: string; icon: string }[] = [
  { key: 'episodic', label: 'Episodic Memory', desc: 'Redis 存储事件序列 · 检索最近轨迹', color: '#00f5ff', icon: '◈' },
  { key: 'semantic', label: 'Semantic Memory', desc: '向量库 · 1536 维嵌入 · 相似度检索', color: '#8b5cf6', icon: '◇' },
  { key: 'procedural', label: 'Procedural Memory', desc: '规则集 · 固化最佳实践策略', color: '#3b82f6', icon: '▣' },
]

function fmtBytes(n: number) {
  if (n > 1e6) return `${(n / 1e6).toFixed(1)} MB`
  if (n > 1e3) return `${(n / 1e3).toFixed(1)} KB`
  return `${n} B`
}

export default function MemoryPage() {
  const [mem, setMem] = useState<MemorySummary | null>(null)

  useEffect(() => {
    api.memory().then(setMem)
  }, [])

  const values: Record<LayerKey, string> = mem
    ? { episodic: `${mem.episodic.entries}`, semantic: `${mem.semantic.entries}`, procedural: `${mem.procedural.rules}` }
    : { episodic: '—', semantic: '—', procedural: '—' }
  const subs: Record<LayerKey, string> = mem
    ? { episodic: fmtBytes(mem.episodic.size_bytes), semantic: `${mem.semantic.dims} dims`, procedural: 'knowledge base' }
    : { episodic: '', semantic: '', procedural: '' }

  return (
    <div className="fade-in mx-auto flex max-w-[1000px] flex-col gap-5">
      <div className="grid grid-cols-3 gap-5">
        {layers.map((l) => (
          <GlassCard key={l.key} hover className="relative overflow-hidden">
            <div className="absolute -right-3 -top-3 text-[54px] opacity-[0.06]" style={{ color: l.color }}>{l.icon}</div>
            <div className="flex items-center justify-between">
              <span className="font-display text-[13px] font-bold text-white">{l.label}</span>
              <Badge tone={l.key === 'episodic' ? 'cyan' : l.key === 'semantic' ? 'purple' : 'blue'}>3·LAYER</Badge>
            </div>
            <div className="digits mt-3 text-3xl font-bold" style={{ color: l.color, textShadow: `0 0 20px ${l.color}55` }}>
              {values[l.key]}
            </div>
            <div className="mt-1 text-[11px] text-slate-500">{subs[l.key]}</div>
            <p className="mt-3 text-[11px] leading-relaxed text-slate-400">{l.desc}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-[13px] font-bold text-white">Memory Consolidation Pipeline</h2>
            <p className="text-[11px] text-slate-500">三层记忆 → 周期性固化 → 提升检索效率</p>
          </div>
          {mem && <Badge tone="green">LAST: {new Date(mem.last_consolidation).toLocaleTimeString('zh-CN', { hour12: false })}</Badge>}
        </div>
        <div className="flex items-center gap-3">
          {['Working', 'Episodic', 'Consolidate', 'Semantic', 'Procedural'].map((s, i) => (
            <div key={s} className="flex flex-1 items-center gap-3">
              <div className="glass-inner flex-1 px-3 py-2.5 text-center text-[11px] font-medium text-slate-300">{s}</div>
              {i < 4 && <span className="text-[#00f5ff]/50">→</span>}
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  )
}