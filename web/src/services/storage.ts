// ============================================================
// 本地存储服务 (localStorage 实现)
// ============================================================

import type { Project } from '@/types'

const STORAGE_KEY = 'ai-film-studio-projects'

export function saveProjects(projects: Project[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projects))
  } catch (e) {
    console.error('Failed to save projects:', e)
  }
}

export function loadProjects(): Project[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    return data ? JSON.parse(data) : []
  } catch {
    return []
  }
}

export function deleteStoredProject(id: string): void {
  const projects = loadProjects().filter((p) => p.id !== id)
  saveProjects(projects)
}
