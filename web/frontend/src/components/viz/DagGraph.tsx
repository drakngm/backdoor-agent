import { useMemo } from 'react'
import type { DagGraph, NodeState } from '../../types'

interface Props {
  graph: DagGraph
  width?: number
  height?: number
  onSelect?: (nodeId: string) => void
}

const COLORS: Record<NodeState, { stroke: string; fill: string; text: string; ring: string }> = {
  running: { stroke: '#00f5ff', fill: 'rgba(0,245,255,0.08)', text: '#a5f3fc', ring: 'rgba(0,245,255,0.55)' },
  completed: { stroke: '#22c55e', fill: 'rgba(34,197,94,0.07)', text: '#86efac', ring: 'rgba(34,197,94,0.4)' },
  waiting: { stroke: 'rgba(148,163,184,0.35)', fill: 'rgba(148,163,184,0.04)', text: '#94a3b8', ring: 'rgba(148,163,184,0.2)' },
  error: { stroke: '#ef4444', fill: 'rgba(239,68,68,0.08)', text: '#fca5a5', ring: 'rgba(239,68,68,0.5)' },
  idle: { stroke: 'rgba(148,163,184,0.25)', fill: 'rgba(148,163,184,0.03)', text: '#64748b', ring: 'rgba(148,163,184,0.15)' },
}

interface EdgeGeom {
  id: string
  d: string
  hasFlow: boolean
  flowColor: string
}

export default function DagGraph({ graph, width = 860, height = 340, onSelect }: Props) {
  const layout = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {}
    const cols = 6
    const midY = height / 2
    const spanY = height * 0.5
    const gapX = width / cols
    graph.nodes.forEach((node, i) => {
      const col = i % cols
      const offset = col % 2 === 0 ? -spanY * 0.16 : spanY * 0.16
      positions[node.id] = { x: (col + 0.5) * gapX, y: midY + offset }
    })
    return positions
  }, [graph, width, height])

  const edges: EdgeGeom[] = useMemo(
    () =>
      graph.edges.flatMap((e) => {
        const s = layout[e.source]
        const t = layout[e.target]
        if (!s || !t) return []
        const dx = t.x - s.x
        const dy = t.y - s.y
        const len = Math.hypot(dx, dy)
        const nx = dx / len
        const ny = dy / len
        const pad = 46
        const cx = (s.x + t.x) / 2
        const cy = (s.y + t.y) / 2 - 26
        const sx = s.x + nx * pad
        const sy = s.y + ny * pad
        const tx = t.x - nx * pad
        const ty = t.y - ny * pad
        const sourceActive = graph.nodes.find((n) => n.id === e.source)?.state === 'running'
        return [
          {
            id: `${e.source}->${e.target}`,
            d: `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`,
            hasFlow: sourceActive,
            flowColor: COLORS[graph.nodes.find((n) => n.id === e.source)?.state ?? 'idle'].stroke,
          },
        ]
      }),
    [graph, layout],
  )

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ minHeight: height }}>
      <defs>
        {edges.map((e) => (
          <path key={e.id} id={`edge-${e.id}`} d={e.d} fill="none" />
        ))}
      </defs>

      {/* edges */}
      {edges.map((e) => {
        const base = e.hasFlow ? e.flowColor : 'rgba(148,163,184,0.22)'
        return (
          <g key={e.id}>
            <path d={e.d} fill="none" stroke="rgba(0,0,0,0.4)" strokeWidth={5} strokeLinecap="round" opacity={0.5} />
            <path d={e.d} fill="none" stroke={base} strokeWidth={1.4} strokeLinecap="round" opacity={e.hasFlow ? 0.9 : 0.6} />
            {e.hasFlow && (
              <g>
                <circle r={3} fill={e.flowColor} opacity={0.15}>
                  <animateMotion dur="1.4s" repeatCount="indefinite" rotate="0">
                    <mpath href={`#edge-${e.id}`} />
                  </animateMotion>
                </circle>
                <circle r={2.2} fill={e.flowColor} opacity={0.5}>
                  <animateMotion dur="1.4s" repeatCount="indefinite" rotate="0">
                    <mpath href={`#edge-${e.id}`} />
                  </animateMotion>
                </circle>
              </g>
            )}
          </g>
        )
      })}

      {/* nodes */}
      {graph.nodes.map((node) => {
        const p = layout[node.id]
        const c = COLORS[node.state]
        const running = node.state === 'running'
        return (
          <g key={node.id} className="cursor-pointer" onClick={() => onSelect?.(node.id)}>
            {running && (
              <circle cx={p.x} cy={p.y} r={42} fill="none" stroke={c.stroke} strokeWidth={1} opacity={0.35}>
                <animate attributeName="r" values="38;48;38" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.35;0.05;0.35" dur="2s" repeatCount="indefinite" />
              </circle>
            )}
            <rect x={p.x - 64} y={p.y - 27} width={128} height={54} rx={14} fill={c.fill} stroke={c.stroke} strokeWidth={running ? 1.6 : 1} />
            <text x={p.x} y={p.y - 2} textAnchor="middle" fill={c.text} fontSize={12.5} fontWeight={700} fontFamily="Space Grotesk, sans-serif">
              {node.label}
            </text>
            <text x={p.x} y={p.y + 13} textAnchor="middle" fill="rgba(148,163,184,0.6)" fontSize={9} fontFamily="Inter, sans-serif">
              {node.sub}
            </text>
            <circle cx={p.x + 54} cy={p.y - 21} r={3.5} fill={running ? c.stroke : c.stroke} opacity={running ? 1 : 0.8}>
              {running && <animate attributeName="opacity" values="1;0.3;1" dur="1s" repeatCount="indefinite" />}
            </circle>
          </g>
        )
      })}
    </svg>
  )
}