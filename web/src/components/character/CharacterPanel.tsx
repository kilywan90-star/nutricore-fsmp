// ============================================================
// F: 角色资产面板
// ============================================================

import { useState } from 'react'
import { useProjectStore } from '@/stores/projectStore'
import { getAdapter } from '@/services/aiAdapter'
import { useShallow } from 'zustand/shallow'
import type { CharacterAsset, GenerationContext } from '@/types'
import { v4 as uuid } from 'uuid'

export function CharacterPanel() {
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [model, setModel] = useState('nano-pro')
  const [generating, setGenerating] = useState<string | null>(null)

  const characters = useProjectStore(
    useShallow((s) => {
      const p = s.projects.find((p) => p.id === s.currentProjectId)
      return p?.characters ?? []
    })
  )

  const projectId = useProjectStore((s) => s.currentProjectId)

  if (!projectId) return null

  const handleCreate = () => {
    if (!name.trim() || !description.trim()) return

    const char: CharacterAsset = {
      id: uuid(),
      type: 'character',
      name: name.trim(),
      description: description.trim(),
      model,
      mainImage: null,
      threeViewGrid: null,
      attributes: { hairStyle: '', clothing: '', expression: '', bodyType: '' },
      variants: { leftProfile: null, rightProfile: null, expressions: [] },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }

    useProjectStore.setState((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, characters: [...p.characters, char], updatedAt: Date.now() }
          : p
      ),
    }))

    setName('')
    setDescription('')
    setShowCreate(false)
  }

  const handleGenerate = async (charId: string) => {
    const char = characters.find((c) => c.id === charId)
    if (!char) return

    setGenerating(charId)
    const adapter = getAdapter(char.model)
    const ctx: GenerationContext = {
      prompt: `${char.description}, front view portrait, realistic style`,
      model: char.model,
      characterAssets: [char],
      sceneAssets: [],
    }

    try {
      const result = await adapter.generateImage(ctx)

      useProjectStore.setState((s) => ({
        projects: s.projects.map((p) =>
          p.id === s.currentProjectId
            ? {
                ...p,
                characters: p.characters.map((c) =>
                  c.id === charId ? { ...c, mainImage: result, updatedAt: Date.now() } : c
                ),
                updatedAt: Date.now(),
              }
            : p
        ),
      }))
    } finally {
      setGenerating(null)
    }
  }

  const handleGenerateThreeView = async (charId: string) => {
    const char = characters.find((c) => c.id === charId)
    if (!char) return

    setGenerating(charId)
    const adapter = getAdapter(char.model)
    const ctx: GenerationContext = {
      prompt: `${char.description}, three-view character sheet, 3x3 grid, multiple angles (front, side, back, three-quarter), consistent appearance, turnaround reference`,
      model: char.model,
      characterAssets: [char],
      sceneAssets: [],
    }

    try {
      const result = await adapter.generateImage(ctx)

      useProjectStore.setState((s) => ({
        projects: s.projects.map((p) =>
          p.id === s.currentProjectId
            ? {
                ...p,
                characters: p.characters.map((c) =>
                  c.id === charId ? { ...c, threeViewGrid: result, updatedAt: Date.now() } : c
                ),
                updatedAt: Date.now(),
              }
            : p
        ),
      }))
    } finally {
      setGenerating(null)
    }
  }

  const handleDelete = (charId: string) => {
    useProjectStore.setState((s) => ({
      projects: s.projects.map((p) =>
        p.id === s.currentProjectId
          ? { ...p, characters: p.characters.filter((c) => c.id !== charId), updatedAt: Date.now() }
          : p
      ),
    }))
  }

  // 拖入画布
  const handleDragStart = (e: React.DragEvent, char: CharacterAsset) => {
    e.dataTransfer.setData('application/reactflow-type', 'character')
    e.dataTransfer.setData('application/reactflow-payload', JSON.stringify({
      id: char.id,
      name: char.name,
      description: char.description,
    }))
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div className="p-3 space-y-3">
      <button
        onClick={() => setShowCreate(!showCreate)}
        className="w-full px-3 py-2 text-sm bg-accent-primary text-white rounded-lg
          hover:bg-purple-700 transition-colors"
      >
        + 新建角色
      </button>

      {showCreate && (
        <div className="space-y-2 bg-canvas-bg rounded-lg p-3 border border-canvas-border">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="角色名称"
            className="w-full px-3 py-1.5 text-sm bg-panel-bg border border-canvas-border
              rounded text-text-primary outline-none focus:border-accent-primary"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="形象描述，如: 正面视角的古装美女人物，真人风格，左侧胸像，右侧全身像"
            rows={3}
            className="w-full px-3 py-1.5 text-sm bg-panel-bg border border-canvas-border
              rounded text-text-primary outline-none focus:border-accent-primary resize-none"
          />
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-1.5 text-sm bg-panel-bg border border-canvas-border
              rounded text-text-primary outline-none"
          >
            <option value="nano-pro">Nano Pro</option>
            <option value="mock-adapter">Mock (开发用)</option>
          </select>
          <button
            onClick={handleCreate}
            disabled={!name.trim() || !description.trim()}
            className="w-full px-3 py-1.5 text-sm bg-accent-primary text-white rounded
              hover:bg-purple-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            创建角色
          </button>
        </div>
      )}

      <div className="space-y-2">
        {characters.length === 0 && (
          <p className="text-xs text-text-secondary text-center py-4">暂无角色资产</p>
        )}
        {characters.map((char) => (
          <div
            key={char.id}
            draggable
            onDragStart={(e) => handleDragStart(e, char)}
            className="bg-canvas-bg border border-canvas-border rounded-lg p-3
              hover:border-accent-primary/40 transition-colors cursor-grab active:cursor-grabbing"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{char.name}</p>
                <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">
                  {char.description}
                </p>
              </div>
              <button
                onClick={() => handleDelete(char.id)}
                className="text-xs text-text-secondary hover:text-error ml-2 shrink-0"
              >
                删除
              </button>
            </div>

            {char.mainImage && (
              <img
                src={char.mainImage.thumbnailUrl}
                alt={char.name}
                className="w-full h-20 object-cover rounded mt-2 border border-canvas-border"
              />
            )}

            {char.threeViewGrid && (
              <div className="mt-1">
                <p className="text-[10px] text-text-secondary">三式图已生成</p>
              </div>
            )}

            <div className="flex gap-2 mt-2">
              <button
                onClick={() => handleGenerate(char.id)}
                disabled={generating === char.id}
                className="flex-1 px-2 py-1 text-xs bg-accent-primary/20 text-accent-secondary
                  rounded hover:bg-accent-primary/30 transition-colors
                  disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {generating === char.id ? '生成中...' : '生成造型图'}
              </button>
              {char.mainImage && (
                <button
                  onClick={() => handleGenerateThreeView(char.id)}
                  disabled={generating === char.id}
                  className="flex-1 px-2 py-1 text-xs bg-accent-primary/20 text-accent-secondary
                    rounded hover:bg-accent-primary/30 transition-colors
                    disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  九宫格三式
                </button>
              )}
            </div>

            <p className="text-[10px] text-text-secondary mt-1.5 text-right">
              拖入画布创建节点
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
