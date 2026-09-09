import { useEffect, useState } from 'react'
import GlassCard from '../components/ui/GlassCard'
import Badge from '../components/ui/Badge'
import { api } from '../api/client'
import type { DetectorStatus } from '../types'

const detectorColor: Record<string, string> = {
  STRIP: '#00f5ff',
  'Neural Cleanse': '#8b5cf6',
  'Activation Clustering': '#3b82f6',
}

interface Row {
  id: string
  model: string
  detector: string
  result: 'CLEAN' | 'FLAGGED' | 'CONFIRMED'
  score: number
  time: string
}

const rows: Row[] = [
  { id: 'det_1024', model: 'vgg16_bdoor.h5', detector: 'Neural Cleanse', result: 'CONFIRMED', score: 0.971, time: '10:42:17' },
  { id: 'det_1023', model: 'resnet50_xfer.h5', detector: 'Activation Clustering', result: 'FLAGGED', score: 0.873, time: '10:31:05' },
  { id: 'det_1022', model: 'embed_inject.pt', detector: 'STRIP', result: 'FLAGGED', score: 0.642, time: '10:12:44' },
  { id: 'det_1021', model: 'mobilenet_v3.h5', detector: 'STRIP', result: 'CLEAN', score: 0.087, time: '09:58:12' },
  { id: 'det_1020', model: 'efficientnet_b0.h5', detector: 'Neural Cleanse', result: 'CLEAN', score: 0.031, time: '09:44:01' },
]

const resultTone: Record<Row['result'], string> = {
  CLEAN: 'text-[#22c55e] border-[rgba(34,197,94,0.3)] bg-[rgba(34,197,94,0.08)]',
  FLAGGED: 'text-[#f59e0b] border-[rgba(245,158,11,0.3)] bg-[rgba(245,158,11,0.08)]',
  CONFIRMED: 'text-[#ef4444] border-[rgba(239,68,68,0.3)] bg-[rgba(239,68,68,0.08)]',
}

function ResultBadge({ r }: { r: Row['result'] }) {
  return <span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold tracking-wider uppercase ${resultTone[r]}`}>{r}</span>
}

export default function DetectionPage() {
  const [detectors, setDetectors] = useState<DetectorStatus[]>([])

  useEffect(() => {
    api.detectors().then(setDetectors)
  }, [])

  return (
    <div className="fade-in mx-auto flex max-w-[1000px] flex-col gap-5">
      {/* detectors */}
      <div className="grid grid-cols-3 gap-5">
        {detectors.map((d) => (
          <GlassCard key={d.name} hover glow={d.status === 'active'} className="relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="font-display text-[14px] font-bold text-white">{d.display}</span>
              <Badge tone={d.status === 'active' ? 'cyan' : d.status === 'error' ? 'red' : 'gray'} pulse={d.status === 'active'}>
                {d.status}
              </Badge>
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-slate-400">{d.description}</p>
            <div className="mt-4 grid grid-cols-3 gap-2 border-t border-[rgba(148,163,184,0.08)] pt-3">
              <div>
                <div className="text-[9px] text-slate-500 uppercase">Detections</div>
                <div className="digits text-[14px] font-semibold text-slate-100">{d.detections}</div>
              </div>
              <div>
                <div className="text-[9px] text-slate-500 uppercase">Precision</div>
                <div className="digits text-[14px] font-semibold text-[#00f5ff]">{d.precision.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-[9px] text-slate-500 uppercase">Last Run</div>
                <div className="digits text-[14px] font-semibold text-slate-100">{d.last_run_ms}ms</div>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* recent detections */}
      <GlassCard className="p-0">
        <div className="flex items-center justify-between border-b border-[rgba(148,163,184,0.08)] px-5 py-3.5">
          <div>
            <h2 className="text-[13px] font-bold text-white">Recent Detections</h2>
            <p className="text-[11px] text-slate-500">Latest scan results across detector network</p>
          </div>
          <Badge tone="green">LIVE FEED</Badge>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] tracking-wider text-slate-500 uppercase">
                <th className="px-5 py-3 font-semibold">Scan ID</th>
                <th className="px-5 py-3 font-semibold">Model</th>
                <th className="px-5 py-3 font-semibold">Detector</th>
                <th className="px-5 py-3 font-semibold">Result</th>
                <th className="px-5 py-3 font-semibold">Score</th>
                <th className="px-5 py-3 font-semibold">Time</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[11px]">
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-[rgba(148,163,184,0.06)] transition-colors hover:bg-white/[0.02]">
                  <td className="px-5 py-2.5 text-[#7dd3fc]">{r.id}</td>
                  <td className="px-5 py-2.5 text-slate-300">{r.model}</td>
                  <td className="px-5 py-2.5">
                    <span className="flex items-center gap-1.5 text-slate-300">
                      <span className="h-1.5 w-1.5 rounded-full" style={{ background: detectorColor[r.detector] ?? '#94a3b8' }} />
                      {r.detector}
                    </span>
                  </td>
                  <td className="px-5 py-2.5"><ResultBadge r={r.result} /></td>
                  <td className="px-5 py-2.5 text-slate-200">{r.score.toFixed(3)}</td>
                  <td className="px-5 py-2.5 text-slate-500">{r.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  )
}