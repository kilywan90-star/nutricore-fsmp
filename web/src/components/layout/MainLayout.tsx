// ============================================================
// D5: 主编辑器布局
// ============================================================

import { useState, useCallback } from 'react'
import type { Step } from './StepIndicator'
import { StepIndicator } from './StepIndicator'
import { LeftPanel } from './LeftPanel'
import { RightPanel } from './RightPanel'
import { FlowCanvas } from '@/components/canvas/FlowCanvas'
import { useNodeStore } from '@/stores/nodeStore'
import { useProjectStore } from '@/stores/projectStore'
import { saveProjects } from '@/services/storage'
import { VideoControlBar } from '@/components/video/VideoControlBar'
import { useShallow } from 'zustand/shallow'
import type { AppNode } from '@/types'

export function MainLayout() {
  const [step, setStep] = useState<Step>('character')
  const [selectedNode, setSelectedNode] = useState<AppNode | null>(null)

  const currentProjectName = useProjectStore(
    useShallow((s) => {
      const p = s.projects.find((p) => p.id === s.currentProjectId)
      return p?.name ?? ''
    })
  )

  const hasProject = useProjectStore(
    (s) => !!s.projects.find((p) => p.id === s.currentProjectId)
  )

  const onNodeClick = useCallback((_e: React.MouseEvent, node: AppNode) => {
    setSelectedNode(node)
  }, [])

  const onCanvasClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  const handleSave = () => {
    const projects = useProjectStore.getState().projects
    saveProjects(projects)
  }

  const handleBack = () => {
    handleSave()
    useProjectStore.setState({ currentProjectId: null })
    useNodeStore.getState().clearAll()
  }

  if (!hasProject) return null

  return (
    <div className="h-full flex flex-col">
      {/* 顶部工具栏 */}
      <header className="h-14 bg-panel-bg border-b border-panel-border flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="text-text-secondary hover:text-text-primary text-sm transition-colors"
          >
            &larr; 项目列表
          </button>
          <span className="text-text-primary font-medium">{currentProjectName}</span>
        </div>
        <StepIndicator current={step} onChange={setStep} />
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            className="px-3 py-1.5 text-xs bg-accent-primary/20 text-accent-secondary
              rounded-lg hover:bg-accent-primary/30 transition-colors"
          >
            保存
          </button>
        </div>
      </header>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        <LeftPanel step={step} />
        <div className="flex-1 flex flex-col">
          <div className="flex-1">
            <FlowCanvas
              step={step}
              onNodeClick={onNodeClick}
              onCanvasClick={onCanvasClick}
            />
          </div>
          {step === 'video' && <VideoControlBar />}
        </div>
        <RightPanel selectedNode={selectedNode} />
      </div>
    </div>
  )
}
