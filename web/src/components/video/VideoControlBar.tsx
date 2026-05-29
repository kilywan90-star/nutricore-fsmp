// ============================================================
// H2: 视频生成控制面板 (底部操作栏)
// ============================================================

import { useState } from 'react'
import { useNodeStore } from '@/stores/nodeStore'
import { useProjectStore } from '@/stores/projectStore'
import { getAdapter } from '@/services/aiAdapter'
import { useShallow } from 'zustand/shallow'
import type { GenerationContext, VideoNodeData } from '@/types'

export function VideoControlBar() {
  const { nodes, updateNodeData, setNodeStatus, propagateTailFrame } = useNodeStore(
    useShallow((s) => ({
      nodes: s.nodes,
      updateNodeData: s.updateNodeData,
      setNodeStatus: s.setNodeStatus,
      propagateTailFrame: s.propagateTailFrame,
    }))
  )

  const projectAssets = useProjectStore(
    useShallow((s) => {
      const p = s.projects.find((p) => p.id === s.currentProjectId)
      return {
        characters: p?.characters ?? [],
        scenes: p?.scenes ?? [],
        id: p?.id ?? null,
      }
    })
  )

  const [generatingAll, setGeneratingAll] = useState(false)

  if (!projectAssets.id) return null

  const videoNodes = nodes
    .filter((n) => n.type === 'videoNode')
    .sort((a, b) => (a.data as VideoNodeData).order - (b.data as VideoNodeData).order)

  // 生成单个视频节点
  const generateOne = async (nodeId: string) => {
    const node = nodes.find((n) => n.id === nodeId)
    if (!node || node.type !== 'videoNode') return

    const data = node.data as VideoNodeData
    setNodeStatus(nodeId, 'running')

    const character = projectAssets.characters.find((c) => c.id === data.characterRef)
    const scene = projectAssets.scenes.find((s) => s.id === data.sceneRef)
    const adapter = getAdapter('nano-pro')

    // 获取尾帧
    let tailFrameUrl: string | undefined
    if (data.previousFrameRef) {
      const prevNode = nodes.find((n) => n.id === data.previousFrameRef)
      if (prevNode && prevNode.type === 'videoNode') {
        tailFrameUrl = (prevNode.data as VideoNodeData).tailFrame?.url
      }
    }

    const ctx: GenerationContext = {
      prompt: data.shotScript,
      model: 'nano-pro',
      characterAssets: character ? [character] : [],
      sceneAssets: scene ? [scene] : [],
      tailFrameUrl,
    }

    try {
      const result = await adapter.generateVideo(ctx)
      updateNodeData(nodeId, {
        result,
        tailFrame: result.tailFrame,
        status: 'completed',
      } as Partial<VideoNodeData>)
    } catch {
      setNodeStatus(nodeId, 'failed')
    }
  }

  // 链式生成所有视频节点
  const handleGenerateAll = async () => {
    setGeneratingAll(true)
    try {
      for (let i = 0; i < videoNodes.length; i++) {
        const node = videoNodes[i]
        // 如果上一节点已完成且有尾帧，自动继承
        if (i > 0) {
          const prevNode = videoNodes[i - 1]
          const prevData = prevNode.data as VideoNodeData
          if (prevData.tailFrame) {
            propagateTailFrame(prevNode.id, node.id)
          }
        }
        await generateOne(node.id)
      }
    } finally {
      setGeneratingAll(false)
    }
  }

  return (
    <div className="h-14 bg-panel-bg border-t border-panel-border flex items-center justify-between px-4">
      <div className="text-sm text-text-secondary">
        {videoNodes.length} 个视频节点 |
        已生成 {videoNodes.filter((n) => (n.data as VideoNodeData).status === 'completed').length}
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleGenerateAll}
          disabled={generatingAll || videoNodes.length === 0}
          className="px-6 py-2 bg-warning text-black font-medium rounded-lg text-sm
            hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {generatingAll ? '链式生成中...' : '一键链式生成全部'}
        </button>
      </div>
    </div>
  )
}
