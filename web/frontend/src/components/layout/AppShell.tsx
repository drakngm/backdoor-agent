import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopHeader from './TopHeader'
import RightPanel from './RightPanel'
import StatusBar from './StatusBar'

export default function AppShell() {
  return (
    <div
      className="grid h-screen grid-cols-[240px_1fr_320px] grid-rows-[72px_1fr_32px] overflow-hidden"
      style={{ background: 'radial-gradient(900px 600px at 20% -10%, rgba(59,130,246,0.06), transparent 55%)' }}
    >
      <div className="row-span-3">
        <Sidebar />
      </div>
      <TopHeader />
      <main className="min-h-0 overflow-y-auto p-5">
        <Outlet />
      </main>
      <div className="min-h-0 overflow-hidden">
        <RightPanel />
      </div>
      <div className="col-span-2">
        <StatusBar />
      </div>
    </div>
  )
}