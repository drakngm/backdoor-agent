import { useEffect, useRef } from 'react'

interface Props {
  size?: number
  className?: string
}

interface Particle {
  x: number
  y: number
  z: number
  tw: number
  spd: number
}

export default function HoloCore({ size = 300, className = '' }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = size * dpr
    canvas.height = size * dpr
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.scale(dpr, dpr)

    const c = size / 2
    let t = 0
    let raf = 0

    // ring 3D projections
    const rings = [
      { tilt: 1.1, speed: 1.0, amp: 0.42, color: 'rgba(0,245,255,0.55)', radius: 0.86 },
      { tilt: -0.6, speed: -1.3, amp: 0.30, color: 'rgba(139,92,246,0.5)', radius: 1.0 },
      { tilt: 0.25, speed: 0.7, amp: 0.18, color: 'rgba(59,130,246,0.45)', radius: 1.14 },
    ]

    // neural nodes
    const nodes = Array.from({ length: 11 }, (_, i) => {
      const a = (i / 11) * Math.PI * 2
      return {
        x: c + Math.cos(a) * c * 0.55,
        y: c + Math.sin(a) * c * 0.55,
        phase: i * 1.7,
      }
    })

    // orbiting particles
    const particles: Particle[] = Array.from({ length: 26 }, () => {
      const a = Math.random() * Math.PI * 2
      const r = c * (0.62 + Math.random() * 0.34)
      return { x: c + Math.cos(a) * r, y: c + Math.sin(a) * r * 0.4, z: Math.random(), tw: Math.random() * Math.PI * 2, spd: 0.4 + Math.random() * 0.8 }
    })

    const step = () => {
      t += 0.006
      ctx.clearRect(0, 0, size, size)

      // core glow
      const coreGrad = ctx.createRadialGradient(c, c, 2, c, c, c * 0.62)
      coreGrad.addColorStop(0, 'rgba(160,240,255,0.85)')
      coreGrad.addColorStop(0.35, 'rgba(0,200,245,0.28)')
      coreGrad.addColorStop(0.7, 'rgba(139,92,246,0.08)')
      coreGrad.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = coreGrad
      ctx.beginPath()
      ctx.arc(c, c, c * 0.62, 0, Math.PI * 2)
      ctx.fill()

      // sphere
      const sph = ctx.createRadialGradient(c - c * 0.2, c - c * 0.22, c * 0.02, c, c, c * 0.34)
      sph.addColorStop(0, 'rgba(220,255,255,0.95)')
      sph.addColorStop(0.55, 'rgba(0,245,255,0.75)')
      sph.addColorStop(1, 'rgba(59,130,246,0.5)')
      ctx.fillStyle = sph
      ctx.shadowColor = 'rgba(0,245,255,0.8)'
      ctx.shadowBlur = 28
      ctx.beginPath()
      ctx.arc(c, c, c * 0.34, 0, Math.PI * 2)
      ctx.fill()
      ctx.shadowBlur = 0

      // latitude arcs on sphere
      ctx.strokeStyle = 'rgba(190,250,255,0.35)'
      ctx.lineWidth = 1
      for (let i = 1; i <= 3; i++) {
        const rr = c * 0.34 * (i / 4)
        ctx.beginPath()
        ctx.ellipse(c, c, rr * 1.15, rr * 0.42, 0, 0, Math.PI * 2)
        ctx.stroke()
      }

      // rings
      for (const r of rings) {
        const rx = c * r.radius
        const ry = c * r.radius * r.amp
        ctx.strokeStyle = r.color
        ctx.lineWidth = 1.2
        ctx.beginPath()
        ctx.ellipse(c, c, rx, ry, r.tilt, 0, Math.PI * 2)
        ctx.stroke()

        // dashed rotating segment marker
        const a = t * 4 * r.speed
        const px = c + Math.cos(a) * rx
        const py = c + Math.sin(a) * ry
        ctx.fillStyle = r.color
        ctx.shadowColor = r.color
        ctx.shadowBlur = 14
        ctx.beginPath()
        ctx.arc(px, py, 2.6, 0, Math.PI * 2)
        ctx.fill()
        ctx.shadowBlur = 0
      }

      // neural lines
      ctx.strokeStyle = 'rgba(0,245,255,0.14)'
      ctx.lineWidth = 0.8
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i]
        const j = (i + 2) % nodes.length
        const m = nodes[j]
        ctx.globalAlpha = 0.25 + 0.2 * Math.sin(t * 2 + n.phase)
        ctx.beginPath()
        ctx.moveTo(n.x, n.y)
        ctx.lineTo(m.x, m.y)
        ctx.stroke()
      }
      ctx.globalAlpha = 1

      // nodes
      for (const n of nodes) {
        const pulse = 0.5 + 0.5 * Math.sin(t * 2 + n.phase)
        ctx.fillStyle = `rgba(0,245,255,${0.35 + 0.5 * pulse})`
        ctx.shadowColor = 'rgba(0,245,255,0.9)'
        ctx.shadowBlur = 10 * pulse
        ctx.beginPath()
        ctx.arc(n.x, n.y, 1.8 + 1.2 * pulse, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.shadowBlur = 0

      // orbiting particles
      for (const p of particles) {
        p.x += Math.cos(p.tw * Math.sin(t)) * 0.3
        p.y += Math.sin(p.tw) * 0.3
        const ax = p.x - c
        const ay = (p.y - c) / 0.4
        const dist = Math.hypot(ax, ay)
        const f = ((c * 0.96) - dist) / (c * 0.4)
        const cx2 = c - ax * (1 + f * 0.12)
        const cy2 = c - ay * (1 + f * 0.12)
        const alpha = 0.25 + 0.55 * p.z
        ctx.strokeStyle = `rgba(140,220,255,${alpha * 0.5})`
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(p.x, p.y)
        ctx.lineTo(cx2, cy2)
        ctx.stroke()
        ctx.fillStyle = `rgba(190,245,255,${alpha})`
        ctx.shadowColor = 'rgba(0,245,255,0.9)'
        ctx.shadowBlur = 6
        ctx.beginPath()
        ctx.arc(p.x, p.y, 1.2 + p.z * 1.2, 0, Math.PI * 2)
        ctx.fill()
        ctx.shadowBlur = 0
      }

      raf = requestAnimationFrame(step)
    }

    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [size])

  return (
    <canvas
      ref={ref}
      className={className}
      style={{ width: size, height: size }}
      aria-label="Holographic AI core animation"
    />
  )
}