// ============================================================
// E3: React Flow 画布
// ============================================================

import { useCallback, useRef, useMemo } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type OnConnect,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { AppNode, AppEdge, VideoNodeData, Step } from '@/types'
import { useNodeStore } from '@/stores/nodeStore'
import { useShallow } from 'zustand/shallow'
import { ImageNodeComponent } from './ImageNode'
import { VideoNodeComponent } from './VideoNode'

interface Props {
  step: Step
  onNodeClick: (e: React.MouseEvent, node: AppNode) => void
  onCanvasClick: () => void
}

const nodeTypes = {
  imageNode: ImageNodeComponent,
  videoNode: VideoNodeComponent,
}

export function FlowCanvas({ step, onNodeClick, onCanvasClick }: Props) {
  const { nodes, edges, onNodesChange, onEdgesChange, addEdge, addImageNode, addVideoNode } =
    useNodeStore(
      useShallow((s) => ({
        nodes: s.nodes,
        edges: s.edges,
        onNodesChange: s.onNodesChange,
        onEdgesChange: s.onEdgesChange,
        addEdge: s.addEdge,
        addImageNode: s.addImageNode,
        addVideoNode: s.addVideoNode,
      }))
    )
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  const onConnect: OnConnect = useCallback(
    (connection) => addEdge(connection),
    [addEdge]
  )

  // 在画布空白处拖入节点
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const type = e.dataTransfer.getData('application/reactflow-type')
      const payload = e.dataTransfer.getData('application/reactflow-payload')
      if (!type || !reactFlowWrapper.current) return

      const bounds = reactFlowWrapper.current.getBoundingClientRect()
      const position = {
        x: e.clientX - bounds.left - 100,
        y: e.clientY - bounds.top - 40,
      }

      if (type === 'character' || type === 'scene') {
        try {
          const data = JSON.parse(payload)
          addImageNode(
            {
              label: data.name,
              description: data.description,
              purpose: type === 'character' ? 'character' : 'scene',
              prompt: data.description,
              model: 'nano-pro',
              assetRefs: [data.id],
            },
            position
          )
        } catch { /* ignore */ }
      }
    },
    [addImageNode]
  )

  // 添加空节点
  const handleAddImageNode = () => {
    addImageNode({
      label: step === 'character' ? '新角色节点' : '新场景节点',
      description: '',
      purpose: step === 'character' ? 'character' : 'scene',
      prompt: '',
      model: 'nano-pro',
      assetRefs: [],
    })
  }

  const handleAddVideoNode = () => {
    addVideoNode({
      label: `分镜 #${nodes.filter((n) => n.type === 'videoNode').length + 1}`,
      description: '',
      shotScript: '',
      characterRef: null,
      sceneRef: null,
    })
  }

  return (
    <div ref={reactFlowWrapper} className="w-full h-full" onDragOver={onDragOver} onDrop={onDrop}>
      {/* 浮动工具栏 */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        {(step === 'character' || step === 'scene') && (
          <button
            onClick={handleAddImageNode}
            className="px-3 py-1.5 text-xs bg-accent-primary/80 text-white
              rounded-lg hover:bg-accent-primary transition-colors shadow-lg"
          >
            + 图片节点
          </button>
        )}
        {step === 'video' && (
          <button
            onClick={handleAddVideoNode}
            className="px-3 py-1.5 text-xs bg-warning/80 text-white
              rounded-lg hover:bg-warning transition-colors shadow-lg"
          >
            + 视频节点
          </button>
        )}
      </div>

      <ReactFlow<AppNode, AppEdge>
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(e, node) => onNodeClick(e, node as AppNode)}
        onPaneClick={onCanvasClick}
        nodeTypes={nodeTypes}
        fitView
        className="bg-canvas-bg"
        defaultEdgeOptions={{
          animated: true,
          style: { stroke: '#a78bfa', strokeWidth: 2 },
        }}
      >
        <Background color="#2a2a4a" gap={20} />
        <Controls className="!bg-panel-bg !border-panel-border !text-text-primary" />
        <MiniMap
          className="!bg-panel-bg !border-panel-border"
          maskColor="rgba(0,0,0,0.7)"
          nodeColor={(n) => {
            if (n.type === 'videoNode') return '#f59e0b'
            const d = n.data as { purpose?: string }
            if (d.purpose === 'character') return '#7c3aed'
            if (d.purpose === 'scene') return '#22c55e'
            return '#a78bfa'
          }}
        />
      </ReactFlow>
    </div>
  )
}
