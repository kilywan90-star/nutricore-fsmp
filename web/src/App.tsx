// ============================================================
// App 根组件
// ============================================================

import { useProjectStore } from '@/stores/projectStore'
import { ProjectDashboard } from '@/components/layout/ProjectDashboard'
import { MainLayout } from '@/components/layout/MainLayout'

export default function App() {
  const currentProjectId = useProjectStore((s) => s.currentProjectId)

  if (!currentProjectId) {
    return <ProjectDashboard onEnter={() => {}} />
  }

  return <MainLayout />
}
