// ============================================================
// C1: 项目状态管理
// ============================================================

import { create } from 'zustand'
import type { Project, ScriptSegment } from '@/types'
import { DEFAULT_PROJECT_SETTINGS } from '@/types'
import { v4 as uuid } from 'uuid'

interface ProjectState {
  // 项目列表
  projects: Project[]
  // 当前活动的项目 ID
  currentProjectId: string | null

  // 操作
  createProject: (name: string, description?: string) => Project
  openProject: (id: string) => void
  deleteProject: (id: string) => void
  getCurrentProject: () => Project | undefined
  updateProjectSettings: (settings: Partial<Project['settings']>) => void

  // 脚本片段管理
  setScriptSegments: (segments: ScriptSegment[]) => void
  addScriptSegment: (segment: ScriptSegment) => void
  updateScriptSegment: (id: string, updates: Partial<ScriptSegment>) => void
  removeScriptSegment: (id: string) => void
  reorderScriptSegments: (ordered: ScriptSegment[]) => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProjectId: null,

  createProject: (name, description = '') => {
    const project: Project = {
      id: uuid(),
      name,
      description,
      settings: { ...DEFAULT_PROJECT_SETTINGS },
      characters: [],
      scenes: [],
      scriptSegments: [],
      presets: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    set((s) => ({
      projects: [...s.projects, project],
      currentProjectId: project.id,
    }))
    return project
  },

  openProject: (id) => set({ currentProjectId: id }),

  deleteProject: (id) => set((s) => ({
    projects: s.projects.filter((p) => p.id !== id),
    currentProjectId: s.currentProjectId === id ? null : s.currentProjectId,
  })),

  getCurrentProject: () => {
    const { projects, currentProjectId } = get()
    return projects.find((p) => p.id === currentProjectId)
  },

  updateProjectSettings: (settings) =>
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, settings: { ...p.settings, ...settings }, updatedAt: Date.now() }
          : p
      ),
    })),

  setScriptSegments: (segments) =>
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, scriptSegments: segments, updatedAt: Date.now() }
          : p
      ),
    })),

  addScriptSegment: (segment) =>
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, scriptSegments: [...p.scriptSegments, segment], updatedAt: Date.now() }
          : p
      ),
    })),

  updateScriptSegment: (id, updates) =>
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? {
              ...p,
              scriptSegments: p.scriptSegments.map((seg) =>
                seg.id === id ? { ...seg, ...updates } : seg
              ),
              updatedAt: Date.now(),
            }
          : p
      ),
    })),

  removeScriptSegment: (id) =>
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, scriptSegments: p.scriptSegments.filter((seg) => seg.id !== id), updatedAt: Date.now() }
          : p
      ),
    })),

  reorderScriptSegments: (ordered) =>
    set((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, scriptSegments: ordered, updatedAt: Date.now() }
          : p
      ),
    })),
}))
