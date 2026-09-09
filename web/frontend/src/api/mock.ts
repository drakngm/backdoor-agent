import type {
  DashboardMetrics,
  DetectionOverview,
  DagGraph,
  TimelinePoint,
  DetectorStatus,
  MemorySummary,
  TraceSummary,
  LogEntry,
  ThreatItem,
  SystemResource,
  HealthStatus,
  ExecuteResult,
} from '../types'

const rand = (min: number, max: number) => min + Math.random() * (max - min)

export function genSeries(n: number, base: number, amp: number, seed = 0): number[] {
  let v = base
  const out: number[] = []
  for (let i = 0; i < n; i++) {
    v = Math.max(0, v + (Math.random() - 0.5) * amp + (seed ? Math.sin((i + seed) / 3) * 2 : 0))
    out.push(Math.round(v * 10) / 10)
  }
  return out
}

export const mockHealth: HealthStatus = {
  status: 'operational',
  app: 'AI Backdoor Detection & Defense Agent System',
  version: '1.4.0',
  uptime_seconds: 38642,
  tools: ['STRIP', 'NeuralCleanse', 'ActivationClustering'],
  backend_connected: false,
}

export const mockMetrics: DashboardMetrics = {
  threat_level: 'LOW',
  detection_confidence: 98.7,
  active_agents: 6,
  running_workflows: 2,
  detection_latency_ms: 142,
  detections_last_24h: 3,
  scan_strategy: 'deep_scan',
}

export const mockOverview: DetectionOverview = {
  backdoors_detected: 24,
  backdoors_trend: genSeries(18, 24, 6),
  clean_models: 1284,
  clean_models_trend: genSeries(18, 1284, 40),
  models_analyzed: 8942,
  models_analyzed_trend: genSeries(18, 8942, 120),
}

export const mockDag: DagGraph = {
  id: 'dag-live-001',
  nodes: [
    { id: 'analyzer', label: 'Model Analyzer', sub: 'metadata · conv', group: 'analyze', state: 'completed' },
    { id: 'strip', label: 'STRIP', sub: 'input perturbation', group: 'detect', state: 'running' },
    { id: 'cleanse', label: 'Neural Cleanse', sub: 'trojan trigger', group: 'detect', state: 'waiting' },
    { id: 'cluster', label: 'Activation Clustering', sub: 'feature space', group: 'detect', state: 'waiting' },
    { id: 'llm', label: 'LLM Analysis', sub: 'decision · CoT', group: 'reason', state: 'waiting' },
    { id: 'report', label: 'Report Generator', sub: 'artifact emit', group: 'output', state: 'waiting' },
  ],
  edges: [
    { source: 'analyzer', target: 'strip' },
    { source: 'strip', target: 'cleanse', label: 'feeds' },
    { source: 'strip', target: 'cluster', label: 'feeds' },
    { source: 'cleanse', target: 'llm' },
    { source: 'cluster', target: 'llm' },
    { source: 'llm', target: 'report' },
  ],
}

export const mockTimeline = (points = 40): TimelinePoint[] => {
  const out: TimelinePoint[] = []
  const now = Date.now()
  for (let i = 0; i < points; i++) {
    const time = new Date(now - (points - i) * 15 * 60 * 1000)
    out.push({
      t: time.toISOString(),
      strip: Math.round(rand(2, 14) * 10) / 10,
      neural_cleanse: Math.round(rand(1, 10) * 10) / 10,
      activation_clustering: Math.round(rand(1, 9) * 10) / 10,
      overall: Math.round(rand(4, 22) * 10) / 10,
    })
  }
  return out
}

export const mockDetectors: DetectorStatus[] = [
  { name: 'strp', display: 'STRIP', description: 'Input perturbation to detect trigger-reactive neurons.', status: 'active', last_run_ms: 142, detections: 9, precision: 0.99 },
  { name: 'ncln', display: 'Neural Cleanse', description: 'Reverse-engineers trojan triggers via optimization.', status: 'idle', last_run_ms: 2260, detections: 11, precision: 0.97 },
  { name: 'actcl', display: 'Activation Clustering', description: 'Clusters penultimate-layer activations for poisoned behavior.', status: 'idle', last_run_ms: 840, detections: 4, precision: 0.95 },
]

export const mockMemory: MemorySummary = {
  episodic: { entries: 1284, size_bytes: 18_874_331 },
  semantic: { entries: 342, dims: 1536 },
  procedural: { rules: 47 },
  last_consolidation: new Date(Date.now() - 1000 * 60 * 4).toISOString(),
}

export const mockTraces: TraceSummary[] = [
  { trace_id: 'trc_9f2a11c4', mode: 'hybrid', status: 'completed', started_at: new Date().toISOString(), duration_ms: 3872, spans: 24 },
  { trace_id: 'trc_7c0e8b21', mode: 'workflow', status: 'completed', started_at: new Date(Date.now() - 60000).toISOString(), duration_ms: 2410, spans: 16 },
  { trace_id: 'trc_5b31a9d0', mode: 'agent', status: 'running', started_at: new Date(Date.now() - 3000).toISOString(), duration_ms: 812, spans: 5 },
]

export const mockLogs: LogEntry[] = [
  { time: new Date().toISOString(), level: 'INFO', logger: 'core.trace', message: 'Span completed tool=STRIP status=passed duration_ms=142', trace_id: 'trc_9f2a11c4' },
  { time: new Date(Date.now() - 8000).toISOString(), level: 'INFO', logger: 'hybrid.agent', message: 'HybridAgent decision gate → proceed to DAG workflow', trace_id: 'trc_9f2a11c4' },
  { time: new Date(Date.now() - 16000).toISOString(), level: 'WARN', logger: 'security.neural_cleanse', message: 'Anomaly score above threshold: 0.87 > 0.6', trace_id: 'trc_7c0e8b21' },
  { time: new Date(Date.now() - 30000).toISOString(), level: 'INFO', logger: 'app', message: 'Tools registered: STRIP, NeuralCleanse, ActivationClustering', trace_id: undefined },
  { time: new Date(Date.now() - 45000).toISOString(), level: 'DEBUG', logger: 'memory.semantic', message: 'Vector store query top-k=5 returned 342 candidates', trace_id: 'trc_5b31a9d0' },
]

export const mockThreats: ThreatItem[] = [
  { id: 'thr_8821', time: new Date().toISOString(), severity: 'high', source: 'model_zoo/vgg16_bdoor.h5', summary: 'Trigger pattern detected in conv4_2 feature space.', detector: 'Neural Cleanse' },
  { id: 'thr_8817', time: new Date(Date.now() - 8 * 60000).toISOString(), severity: 'medium', source: 'ft/resnet50_xfer.h5', summary: 'Class cluster deviation flagged across 3 classes.', detector: 'Activation Clustering' },
  { id: 'thr_8792', time: new Date(Date.now() - 34 * 60000).toISOString(), severity: 'low', source: 'llm/embed_inject.pt', summary: 'High-entropy input layer sensitivity observed.', detector: 'STRIP' },
]

export const mockResource: SystemResource = { cpu: 34, gpu: 62, mem: 48, gpu_name: 'NVIDIA A100 · 40GB' }

export function runExecute(mode: 'agent' | 'workflow' | 'hybrid', body: Record<string, string>): ExecuteResult {
  switch (mode) {
    case 'agent': {
      const message = body.message ?? 'detect model.h5'
      return {
        trace_id: `trc_${Math.random().toString(16).slice(2, 10)}`,
        mode: 'agent',
        status: 'completed',
        final_answer: `Agent 分析完成。已对模型执行符号级预检并路由至扫描工具。任务："${message}"。STRIP 未发现明显异常；Neural Cleanse 置信度 0.87。`,
        critical_path: ['llm_call', 'tool_router', 'STRIP', 'final_llm'],
        source: 'mock',
      }
    }
    case 'workflow': {
      const strategy = body.strategy ?? 'fast_scan'
      return {
        trace_id: `trc_${Math.random().toString(16).slice(2, 10)}`,
        mode: 'workflow',
        status: 'completed',
        final_answer: `Workflow（${strategy}）执行完成：16 个 span，无阻塞任务。`,
        critical_path: ['planner', 'task_graph', 'STRIP', 'cleanse', 'report'],
        source: 'mock',
      }
    }
    case 'hybrid':
    default: {
      const model_path = body.model_path ?? 'model.h5'
      const score = Math.random() > 0.5 ? 0.981 : 0.06
      return {
        trace_id: `trc_${Math.random().toString(16).slice(2, 10)}`,
        mode: 'hybrid',
        status: 'completed',
        verdict: score > 0.5 ? 'BACKDOOR' : 'CLEAN',
        confidence: Math.round(score * 1000) / 10,
        final_answer: `模型 ${model_path} 判定为 ${score > 0.5 ? '已植入后门' : '安全'}（置信度 ${(score * 100).toFixed(1)}%）。`,
        decisions: [
          '决策 1：模型结构 @conv4_2 出现触发敏感区 → 调度神经网络净化',
          '决策 2：异常分数 0.87 超过阈值 0.6 → 提升扫描深度',
          '决策 3：交叉验证结果一致 → 生成审计报告',
        ],
        tool_results: [
          { tool: 'STRIP', done: true, passed: true },
          { tool: 'NeuralCleanse', done: true, passed: false },
          { tool: 'ActivationClustering', done: true, passed: true },
        ],
        mermaid: 'graph TD; A[Model Analyzer] --> B[STRIP]; B --> C[Neural Cleanse]',
        critical_path: ['analyzer', 'strip', 'cleanse', 'decision_engine', 'report'],
        source: 'mock',
      }
    }
  }
}
