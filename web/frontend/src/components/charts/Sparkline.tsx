import { useMemo, useId } from 'react'

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
  fill?: boolean
  strokeWidth?: number
}

export default function Sparkline({ data, width = 120, height = 34, color = '#00f5ff', fill = true, strokeWidth = 1.5 }: SparklineProps) {
  const id = useId()
  const { path, area, endX, endY } = useMemo(() => {
    if (data.length < 2) return { path: '', area: '', endX: 0, endY: 10 }
    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    const step = width / (data.length - 1)
    const pts = data.map((v, i) => {
      const x = i * step
      const y = height - 3 - ((v - min) / range) * (height - 6)
      return [x, y] as const
    })
    const d = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ')
    const a = `${d} L${width},${height} L0,${height} Z`
    const [endX, endY] = pts[pts.length - 1]
    return { path: d, area: a, endX, endY }
  }, [data, width, height])

  const gid = `sp-${id.replace(/[:]/g, '')}`

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${gid})`} />}
      <path d={path} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" style={{ filter: `drop-shadow(0 0 5px ${color}66)` }} />
      {data.length > 1 && (
        <circle cx={endX} cy={endY} r="2" fill={color} style={{ filter: `drop-shadow(0 0 6px ${color})` }} />
      )}
    </svg>
  )
}