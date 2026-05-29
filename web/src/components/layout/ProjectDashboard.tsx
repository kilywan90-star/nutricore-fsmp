// ============================================================
// D1: 项目 Dashboard
// ============================================================

import { useState } from 'react'
import { useProjectStore } from '@/stores/projectStore'
import { loadProjects, deleteStoredProject } from '@/services/storage'

interface Props {
  onEnter: () => void
}

export function ProjectDashboard({ onEnter }: Props) {
  const { projects, setProjects, createProject, openProject, deleteProject } =
    useProjectStore()
  const [newName, setNewName] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  // 首次加载时从 storage 恢复
  useState(() => {
    const stored = loadProjects()
    if (stored.length > 0) {
      // 直接 set state
      useProjectStore.setState({ projects: stored })
    }
  })

  const handleCreate = () => {
    if (!newName.trim()) return
    const p = createProject(newName.trim())
    setNewName('')
    setShowCreate(false)
    onEnter()
  }

  const handleOpen = (id: string) => {
    openProject(id)
    onEnter()
  }

  const handleDelete = (id: string) => {
    deleteProject(id)
    deleteStoredProject(id)
  }

  return (
    <div className="h-full flex flex-col items-center justify-center bg-canvas-bg p-8">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-accent-secondary mb-3">
            AI Film Studio
          </h1>
          <p className="text-text-secondary text-lg">
            三步法：固定角色 → 固定场景 → 情节连续
          </p>
        </div>

        <div className="flex justify-center mb-10">
          {!showCreate ? (
            <button
              onClick={() => setShowCreate(true)}
              className="px-8 py-4 bg-accent-primary text-white rounded-xl text-lg
                hover:bg-purple-700 transition-colors shadow-lg"
            >
              + 新建项目
            </button>
          ) : (
            <div className="flex gap-3 items-center bg-panel-bg p-4 rounded-xl border border-panel-border">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                placeholder="输入项目名称..."
                autoFocus
                className="px-4 py-3 bg-canvas-bg border border-canvas-border rounded-lg
                  text-text-primary w-64 outline-none focus:border-accent-primary transition-colors"
              />
              <button
                onClick={handleCreate}
                className="px-6 py-3 bg-accent-primary text-white rounded-lg
                  hover:bg-purple-700 transition-colors"
              >
                创建
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-3 text-text-secondary hover:text-text-primary transition-colors"
              >
                取消
              </button>
            </div>
          )}
        </div>

        {projects.length > 0 && (
          <div>
            <h2 className="text-lg text-text-secondary mb-4">已有项目</h2>
            <div className="space-y-2">
              {projects.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between bg-panel-bg
                    border border-panel-border rounded-xl px-6 py-4
                    hover:border-accent-primary/40 transition-colors group"
                >
                  <div className="flex-1 cursor-pointer" onClick={() => handleOpen(p.id)}>
                    <div className="font-medium text-text-primary">{p.name}</div>
                    <div className="text-sm text-text-secondary mt-1">
                      {p.characters.length} 角色 · {p.scenes.length} 场景 ·{' '}
                      {p.scriptSegments.length} 分镜 ·{' '}
                      {new Date(p.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(p.id)
                    }}
                    className="px-3 py-1 text-sm text-text-secondary
                      hover:text-error opacity-0 group-hover:opacity-100 transition-all"
                  >
                    删除
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
