// ============================================================
// G: 场景资产面板 + 锚点编辑器
// ============================================================

import { useState } from 'react'
import { useProjectStore } from '@/stores/projectStore'
import { getAdapter } from '@/services/aiAdapter'
import { useShallow } from 'zustand/shallow'
import type { SceneAsset, SceneAnchorSettings, GenerationContext, StylePreset } from '@/types'
import {
  DEFAULT_SCENE_ANCHOR,
  LIGHTING_PRESETS,
  COLOR_TONE_PRESETS,
  TEXTURE_PRESETS,
} from '@/types'
import { v4 as uuid } from 'uuid'

export function ScenePanel() {
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [generating, setGenerating] = useState<string | null>(null)
  const [editingAnchor, setEditingAnchor] = useState<string | null>(null)

  const scenes = useProjectStore(
    useShallow((s) => {
      const p = s.projects.find((p) => p.id === s.currentProjectId)
      return p?.scenes ?? []
    })
  )

  const projectId = useProjectStore((s) => s.currentProjectId)

  if (!projectId) return null

  const handleCreate = () => {
    if (!name.trim() || !description.trim()) return

    const scene: SceneAsset = {
      id: uuid(),
      type: 'scene',
      name: name.trim(),
      description: description.trim(),
      baseImage: null,
      anchorSettings: { ...DEFAULT_SCENE_ANCHOR },
      styledImage: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }

    useProjectStore.setState((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, scenes: [...p.scenes, scene], updatedAt: Date.now() }
          : p
      ),
    }))

    setName('')
    setDescription('')
    setShowCreate(false)
  }

  const handleGenerateBase = async (sceneId: string) => {
    const scene = scenes.find((s) => s.id === sceneId)
    if (!scene) return

    setGenerating(sceneId)
    const adapter = getAdapter('nano-pro')
    const ctx: GenerationContext = {
      prompt: scene.description,
      model: 'nano-pro',
      characterAssets: [],
      sceneAssets: [scene],
    }

    try {
      const result = await adapter.generateImage(ctx)
      useProjectStore.setState((s) => ({
        projects: s.projects.map((p) =>
          p.id === s.currentProjectId
            ? { ...p, scenes: p.scenes.map((sc) =>
                sc.id === sceneId ? { ...sc, baseImage: result, updatedAt: Date.now() } : sc
              ), updatedAt: Date.now() }
            : p
        ),
      }))
    } finally {
      setGenerating(null)
    }
  }

  const handleGenerateStyled = async (sceneId: string) => {
    const scene = scenes.find((s) => s.id === sceneId)
    if (!scene) return

    const a = scene.anchorSettings
    const stylePrompt = [a.lighting, a.colorTone, a.texture, a.mood].filter(Boolean).join(', ')

    setGenerating(sceneId)
    const adapter = getAdapter('nano-pro')
    const ctx: GenerationContext = {
      prompt: `${scene.description}, ${stylePrompt}`,
      model: 'nano-pro',
      characterAssets: [],
      sceneAssets: [scene],
    }

    try {
      const result = await adapter.generateImage(ctx)
      useProjectStore.setState((s) => ({
        projects: s.projects.map((p) =>
          p.id === s.currentProjectId
            ? { ...p, scenes: p.scenes.map((sc) =>
                sc.id === sceneId ? { ...sc, styledImage: result, updatedAt: Date.now() } : sc
              ), updatedAt: Date.now() }
            : p
        ),
      }))
    } finally {
      setGenerating(null)
    }
  }

  const handleUpdateAnchor = (sceneId: string, anchor: Partial<SceneAnchorSettings>) => {
    useProjectStore.setState((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, scenes: p.scenes.map((sc) =>
              sc.id === sceneId
                ? { ...sc, anchorSettings: { ...sc.anchorSettings, ...anchor }, updatedAt: Date.now() }
                : sc
            ), updatedAt: Date.now() }
          : p
      ),
    }))
  }

  const handleDelete = (sceneId: string) => {
    useProjectStore.setState((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, scenes: p.scenes.filter((sc) => sc.id !== sceneId), updatedAt: Date.now() }
          : p
      ),
    }))
  }

  const handleDragStart = (e: React.DragEvent, scene: SceneAsset) => {
    e.dataTransfer.setData('application/reactflow-type', 'scene')
    e.dataTransfer.setData('application/reactflow-payload', JSON.stringify({
      id: scene.id,
      name: scene.name,
      description: scene.description,
    }))
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div className="p-3 space-y-3">
      <button
        onClick={() => setShowCreate(!showCreate)}
        className="w-full px-3 py-2 text-sm bg-green-600 text-white rounded-lg
          hover:bg-green-700 transition-colors"
      >
        + 新建场景
      </button>

      {showCreate && (
        <div className="space-y-2 bg-canvas-bg rounded-lg p-3 border border-canvas-border">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="场景名称"
            className="w-full px-3 py-1.5 text-sm bg-panel-bg border border-canvas-border
              rounded text-text-primary outline-none focus:border-green-600"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="环境描述，如: 古代房间，木质结构，烛光摇曳"
            rows={3}
            className="w-full px-3 py-1.5 text-sm bg-panel-bg border border-canvas-border
              rounded text-text-primary outline-none focus:border-green-600 resize-none"
          />
          <button
            onClick={handleCreate}
            disabled={!name.trim() || !description.trim()}
            className="w-full px-3 py-1.5 text-sm bg-green-600 text-white rounded
              hover:bg-green-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            创建场景
          </button>
        </div>
      )}

      <div className="space-y-2">
        {scenes.length === 0 && (
          <p className="text-xs text-text-secondary text-center py-4">暂无场景资产</p>
        )}
        {scenes.map((scene) => (
          <div
            key={scene.id}
            draggable
            onDragStart={(e) => handleDragStart(e, scene)}
            className="bg-canvas-bg border border-canvas-border rounded-lg p-3
              hover:border-green-600/40 transition-colors cursor-grab active:cursor-grabbing"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{scene.name}</p>
                <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">
                  {scene.description}
                </p>
              </div>
              <button
                onClick={() => handleDelete(scene.id)}
                className="text-xs text-text-secondary hover:text-error ml-2 shrink-0"
              >
                删除
              </button>
            </div>

            {scene.baseImage && (
              <img
                src={scene.baseImage.thumbnailUrl}
                alt={scene.name}
                className="w-full h-20 object-cover rounded mt-2 border border-canvas-border"
              />
            )}

            {/* 锚点指示 */}
            <div className="flex flex-wrap gap-1 mt-2">
              {scene.anchorSettings.lighting && (
                <span className="text-[10px] bg-yellow-600/20 text-yellow-400 px-1.5 py-0.5 rounded">
                  {scene.anchorSettings.lighting.split(',')[0]}
                </span>
              )}
              {scene.anchorSettings.colorTone && (
                <span className="text-[10px] bg-blue-600/20 text-blue-400 px-1.5 py-0.5 rounded">
                  {scene.anchorSettings.colorTone.split(',')[0]}
                </span>
              )}
              {scene.anchorSettings.texture && (
                <span className="text-[10px] bg-purple-600/20 text-purple-400 px-1.5 py-0.5 rounded">
                  {scene.anchorSettings.texture.split(',')[0]}
                </span>
              )}
            </div>

            <div className="flex gap-2 mt-2">
              <button
                onClick={() => handleGenerateBase(scene.id)}
                disabled={generating === scene.id}
                className="flex-1 px-2 py-1 text-xs bg-green-600/20 text-green-400
                  rounded hover:bg-green-600/30 transition-colors
                  disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {generating === scene.id ? '生成中...' : '生成空场景'}
              </button>
              {scene.baseImage && (
                <button
                  onClick={() => handleGenerateStyled(scene.id)}
                  disabled={generating === scene.id}
                  className="flex-1 px-2 py-1 text-xs bg-green-600/20 text-green-400
                    rounded hover:bg-green-600/30 transition-colors
                    disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  风格化
                </button>
              )}
            </div>

            {/* 锚点编辑器 */}
            <button
              onClick={() => setEditingAnchor(editingAnchor === scene.id ? null : scene.id)}
              className="mt-2 w-full text-xs text-text-secondary hover:text-text-primary
                transition-colors py-1 border-t border-canvas-border pt-2"
            >
              {editingAnchor === scene.id ? '收起锚点设置' : '展开场景锚点设置'}
            </button>

            {editingAnchor === scene.id && (
              <AnchorEditor
                anchor={scene.anchorSettings}
                onChange={(a) => handleUpdateAnchor(scene.id, a)}
              />
            )}

            <p className="text-[10px] text-text-secondary mt-1.5 text-right">
              拖入画布创建节点
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---- 锚点编辑器 ----

function AnchorEditor({
  anchor,
  onChange,
}: {
  anchor: SceneAnchorSettings
  onChange: (a: Partial<SceneAnchorSettings>) => void
}) {
  return (
    <div className="mt-2 space-y-2 bg-panel-bg rounded-lg p-3 border border-canvas-border">
      {/* 光影 */}
      <div>
        <label className="text-[10px] text-text-secondary block mb-1">光影</label>
        <select
          value={anchor.lighting}
          onChange={(e) => onChange({ lighting: e.target.value })}
          className="w-full px-2 py-1 text-xs bg-canvas-bg border border-canvas-border
            rounded text-text-primary outline-none"
        >
          <option value="">无</option>
          {LIGHTING_PRESETS.map((p) => (
            <option key={p.id} value={p.value}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* 色调 */}
      <div>
        <label className="text-[10px] text-text-secondary block mb-1">色调</label>
        <select
          value={anchor.colorTone}
          onChange={(e) => onChange({ colorTone: e.target.value })}
          className="w-full px-2 py-1 text-xs bg-canvas-bg border border-canvas-border
            rounded text-text-primary outline-none"
        >
          <option value="">无</option>
          {COLOR_TONE_PRESETS.map((p) => (
            <option key={p.id} value={p.value}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* 质感 */}
      <div>
        <label className="text-[10px] text-text-secondary block mb-1">质感</label>
        <select
          value={anchor.texture}
          onChange={(e) => onChange({ texture: e.target.value })}
          className="w-full px-2 py-1 text-xs bg-canvas-bg border border-canvas-border
            rounded text-text-primary outline-none"
        >
          <option value="">无</option>
          {TEXTURE_PRESETS.map((p) => (
            <option key={p.id} value={p.value}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* 情绪 */}
      <div>
        <label className="text-[10px] text-text-secondary block mb-1">情绪</label>
        <input
          type="text"
          value={anchor.mood}
          onChange={(e) => onChange({ mood: e.target.value })}
          placeholder="如: 温馨、悬疑、庄严"
          className="w-full px-2 py-1 text-xs bg-canvas-bg border border-canvas-border
            rounded text-text-primary outline-none focus:border-green-600"
        />
      </div>
    </div>
  )
}
