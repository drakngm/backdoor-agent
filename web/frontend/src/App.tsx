import { Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import OverviewPage from './pages/OverviewPage'
import AgentConsolePage from './pages/AgentConsolePage'
import HybridAgentPage from './pages/HybridAgentPage'
import WorkflowPage from './pages/WorkflowPage'
import DetectionPage from './pages/DetectionPage'
import MemoryPage from './pages/MemoryPage'
import TracePage from './pages/TracePage'
import LogsPage from './pages/LogsPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/agent" element={<AgentConsolePage />} />
        <Route path="/hybrid" element={<HybridAgentPage />} />
        <Route path="/workflow" element={<WorkflowPage />} />
        <Route path="/detection" element={<DetectionPage />} />
        <Route path="/memory" element={<MemoryPage />} />
        <Route path="/trace" element={<TracePage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}