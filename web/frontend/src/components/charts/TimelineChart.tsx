import { useEffect, useRef } from 'react'
import type { TimelinePoint } from '../../types'

const SERIES = [
  { key: 'strip', color: '#00f5ff', label: 'STRIP' },
  { key: 'neural_cleanse', color: '#8b5cf6', label: 'Neural Cleanse' },
  { key: 'activation_clustering', color: '#3b82f6', label: 'Activation Clustering' },
  { key: 'overall', color: '#22c55e', label: 'Overall' },
] as const

interface Props {
  data: TimelinePoint[]
  height?: number
}

function draw(ctx: CanvasRenderingContext2D, w: number, h: number, dpr: number, data: TimelinePoint[]) {
  ctx.clearRect(0, 0, w, h)
  if (data.length < 2) return

  const padL = 40
  const padR = 14
  const padT = 14
  const padB = 26
  const iw = w - padL - padR
  const ih = h - padT - padB

  const all = data.flatMap((p) => [p.strip, p.neural_cleanse, p.activation_clustering, p.overall])
  const max = Math.max(...all) * 1.15 || 1

  // grid
  ctx.strokeStyle = 'rgba(148,163,184,0.07)'
  ctx.lineWidth = 1 / dpr
  const hLines = 4
  for (let i = 0; i <= hLines; i++) {
    const y = padT + (ih / hLines) * i
    ctx.beginPath()
    ctx.moveTo(padL, y)
    ctx.lineTo(w - padR, y)
    ctx.stroke()
    const val = max - (max / hLines) * i
    ctx.fillStyle = 'rgba(148,163,184,0.35)'
    ctx.font = `${9 / dpr}px "JetBrains Mono", monospace`
    ctx.textAlign = 'right'
    ctx.fillText(val.toFixed(0), padL - 8, y + 3 / dpr)
  }

  // time axis
  ctx.strokeStyle = 'rgba(148,163,184,0.12)'
  ctx.beginPath()
  ctx.moveTo(padL, h - padB)
  ctx.lineTo(w - padR, h - padB)
  ctx.stroke()

  const tStep = Math.floor(data.length / 5)
  for (let i = 0; i < data.length; i += tStep) {
    const x = padL + (i / (data.length - 1)) * iw
    const d = new Date(data[i].t)
    ctx.fillStyle = 'rgba(148,163,184,0.4)'
    ctx.font = `${9 / dpr}px "JetBrains Mono", monospace`
    ctx.textAlign = 'center'
    ctx.fillText(d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }), x, h - padB + 14 / dpr)
  }

  // series
  for (const s of SERIES) {
    const pts = data.map((p, i) => {
      const x = padL + (i / (data.length - 1)) * iw
      const y = padT + ih - (p[s.key] / max) * ih
      return [x, y] as const
    })

    ctx.shadowColor = s.color
    ctx.shadowBlur = 8 / dpr
    ctx.strokeStyle = s.color
    ctx.lineWidth = 1.6 / dpr
    ctx.beginPath()
    pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)))
    ctx.stroke()
    ctx.shadowBlur = 0

    // area fill
    const grad = ctx.createLinearGradient(0, padT, 0, h - padB)
    grad.addColorStop(0, s.color + '22')
    grad.addColorStop(1, s.color + '00')
    ctx.fillStyle = grad
    ctx.beginPath()
    pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)))
    ctx.lineTo(pts[pts.length - 1][0], h - padB)
    ctx.lineTo(pts[0][0], h - padB)
    ctx.closePath()
    ctx.fill()

    // end dot
    const [ex, ey] = pts[pts.length - 1]
    ctx.fillStyle = s.color
    ctx.shadowColor = s.color
    ctx.shadowBlur = 12 / dpr
    ctx.beginPath()
    ctx.arc(ex, ey, 2.5 / dpr, 0, Math.PI * 2)
    ctx.fill()
    ctx.shadowBlur = 0
    ctx.fillStyle = s.color
    ctx.font = `${9 / dpr}px "JetBrains Mono", monospace`
    ctx.textAlign = 'left'
    ctx.fillText(s.label, ex - 30 / dpr, ey - 8 / dpr)
  }
}

export default function TimelineChart({ data, height = 240 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const w = canvas.clientWidth
    const h = height
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.height = `${h}px`
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.scale(dpr, dpr)
    draw(ctx, w, h, dpr, data)
  }, [data, height])

  return <canvas ref={ref} className="w-full" style={{ minHeight: height }} />
}

const SeriesLegend = () => (
  <div className="flex flex-wrap items-center gap-4">
    {SERIES.map((s) => (
      <span key={s.key} className="flex items-center gap-1.5 text-[10px] text-slate-400">
        <span className="h-1.5 w-4 rounded-full" style={{ background: s.color, boxShadow: `0 0 8px ${s.color}88` }} />
        {s.label}
      </span>
    ))}
  </div>
)

export { SeriesLegend }