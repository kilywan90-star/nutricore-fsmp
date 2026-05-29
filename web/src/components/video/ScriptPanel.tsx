// ============================================================
// H1: 脚本拆分面板
// ============================================================

import { useState } from 'react'
import { useProjectStore } from '@/stores/projectStore'
import { useNodeStore } from '@/stores/nodeStore'
import { useShallow } from 'zustand/shallow'
import type { ScriptSegment } from '@/types'
import { v4 as uuid } from 'uuid'

export function ScriptPanel() {
  const [scriptText, setScriptText] = useState('')
  const [editingSegment, setEditingSegment] = useState<string | null>(null)

  const projectData = useProjectStore(
    useShallow((s) => {
      const p = s.projects.find((p) => p.id === s.currentProjectId)
      return {
        segments: p?.scriptSegments ?? [],
        characters: p?.characters ?? [],
        scenes: p?.scenes ?? [],
        id: p?.id ?? null,
      }
    })
  )

  const addVideoNode = useNodeStore((s) => s.addVideoNode)
  const nodes = useNodeStore(useShallow((s) => s.nodes))

  if (!projectData.id) return null

  const segments = projectData.segments
  const characters = projectData.characters
  const scenes = projectData.scenes

  // 自动拆分脚本 (按句号/换行)
  const handleSplit = () => {
    if (!scriptText.trim()) return

    const parts = scriptText
      .split(/[。\n]/)
      .map((s) => s.trim())
      .filter(Boolean)

    const newSegments: ScriptSegment[] = parts.map((script, i) => ({
      id: uuid(),
      order: i + 1,
      script,
      duration: 15,
      characterRefs: [],
      sceneRef: null,
      parentSegmentId: i > 0 ? null : null, // 将在后续通过链式设置
      nodeId: null,
    }))

    // 建立链式关系
    for (let i = 1; i < newSegments.length; i++) {
      newSegments[i].parentSegmentId = newSegments[i - 1].id
    }

    useProjectStore.getState().setScriptSegments(newSegments)
    setScriptText('')
  }

  // 为分镜创建视频节点
  const handleCreateVideoNode = (seg: ScriptSegment) => {
    const node = addVideoNode({
      label: `分镜 #${seg.order}`,
      description: seg.script,
      shotScript: seg.script,
      characterRef: seg.characterRefs[0] || null,
      sceneRef: seg.sceneRef,
      previousFrameRef: seg.parentSegmentId
        ? nodes.find((n) => {
            const segs = projectData.segments
            const parent = segs.find((s) => s.id === seg.parentSegmentId)
            return parent?.nodeId === n.id
          })?.id ?? null
        : null,
      order: seg.order,
      duration: seg.duration,
    })

    // 更新 segment 的 nodeId
    useProjectStore.getState().updateScriptSegment(seg.id, { nodeId: node.id })
  }

  const handleDeleteSegment = (id: string) => {
    useProjectStore.getState().removeScriptSegment(id)
  }

  // 手动创建单个分镜段
  const handleAddManual = () => {
    const seg: ScriptSegment = {
      id: uuid(),
      order: segments.length + 1,
      script: '',
      duration: 15,
      characterRefs: [],
      sceneRef: null,
      parentSegmentId: segments.length > 0 ? segments[segments.length - 1].id : null,
      nodeId: null,
    }
    useProjectStore.getState().addScriptSegment(seg)
    setEditingSegment(seg.id)
  }

  return (
    <div className="p-3 space-y-3">
      {/* 脚本输入区 */}
      <div className="space-y-2">
        <label className="text-xs text-text-secondary block">
          输入完整脚本，按句号自动拆分为分镜段
        </label>
        <textarea
          value={scriptText}
          onChange={(e) => setScriptText(e.target.value)}
          placeholder={`第一场：女主走进古代房间，环顾四周。\n她走到桌前，拿起一卷竹简。\n窗外透进暖色阳光，她微微一笑。`}
          rows={5}
          className="w-full px-3 py-2 text-sm bg-canvas-bg border border-canvas-border
            rounded text-text-primary outline-none focus:border-warning resize-none"
        />
        <button
          onClick={handleSplit}
          disabled={!scriptText.trim()}
          className="w-full px-3 py-1.5 text-sm bg-warning/80 text-white rounded
            hover:bg-warning transition-colors disabled:opacity-40"
        >
          拆分脚本
        </button>
      </div>

      <div className="border-t border-panel-border pt-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-secondary">
            {segments.length} 个分镜段
          </span>
          <button
            onClick={handleAddManual}
            className="text-xs text-accent-secondary hover:text-accent-primary transition-colors"
          >
            + 手动添加
          </button>
        </div>

        {segments.length === 0 && (
          <p className="text-xs text-text-secondary text-center py-4">
            输入脚本后点击"拆分脚本"
          </p>
        )}

        <div className="space-y-2">
          {segments.map((seg) => {
            const hasNode = seg.nodeId !== null
            return (
              <div
                key={seg.id}
                className="bg-canvas-bg border border-canvas-border rounded-lg p-3
                  hover:border-warning/40 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-warning">#{seg.order}</span>
                  <span className="text-xs text-text-secondary">{seg.duration}s</span>
                  {hasNode && (
                    <span className="text-[10px] bg-green-600/20 text-green-400 px-1.5 py-0.5 rounded">
                      已建节点
                    </span>
                  )}
                </div>

                {editingSegment === seg.id ? (
                  <textarea
                    value={seg.script}
                    onChange={(e) =>
                      useProjectStore.getState().updateScriptSegment(seg.id, {
                        script: e.target.value,
                      })
                    }
                    onBlur={() => setEditingSegment(null)}
                    autoFocus
                    rows={2}
                    className="w-full px-2 py-1 text-xs bg-panel-bg border border-canvas-border
                      rounded text-text-primary outline-none resize-none"
                  />
                ) : (
                  <p
                    className="text-xs text-text-primary cursor-pointer hover:text-accent-secondary"
                    onClick={() => setEditingSegment(seg.id)}
                  >
                    {seg.script || '(点击编辑)'}
                  </p>
                )}

                {/* 角色/场景引用 */}
                <div className="flex gap-2 mt-2">
                  <select
                    value={seg.characterRefs[0] || ''}
                    onChange={(e) =>
                      useProjectStore.getState().updateScriptSegment(seg.id, {
                        characterRefs: e.target.value ? [e.target.value] : [],
                      })
                    }
                    className="flex-1 px-2 py-1 text-xs bg-panel-bg border border-canvas-border
                      rounded text-text-primary outline-none"
                  >
                    <option value="">选择角色...</option>
                    {characters.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                  <select
                    value={seg.sceneRef || ''}
                    onChange={(e) =>
                      useProjectStore.getState().updateScriptSegment(seg.id, {
                        sceneRef: e.target.value || null,
                      })
                    }
                    className="flex-1 px-2 py-1 text-xs bg-panel-bg border border-canvas-border
                      rounded text-text-primary outline-none"
                  >
                    <option value="">选择场景...</option>
                    {scenes.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>

                <div className="flex gap-2 mt-2">
                  {!hasNode && (
                    <button
                      onClick={() => handleCreateVideoNode(seg)}
                      className="flex-1 px-2 py-1 text-xs bg-warning/20 text-warning
                        rounded hover:bg-warning/30 transition-colors"
                    >
                      创建视频节点
                    </button>
                  )}
                  <button
                    onClick={() => handleDeleteSegment(seg.id)}
                    className="px-2 py-1 text-xs text-text-secondary hover:text-error
                      transition-colors"
                  >
                    删除
                  </button>
                </div>

                {/* 尾帧链式指示 */}
                {seg.parentSegmentId && (
                  <p className="text-[10px] text-text-secondary mt-1.5">
                    继承分镜 #{segments.find((s) => s.id === seg.parentSegmentId)?.order} 尾帧
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
