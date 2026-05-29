// ============================================================
// C3: 节点图状态管理 (React Flow 集成)
// ============================================================

import { create } from 'zustand'
import type { AppNode, AppEdge, NodeStatus, ImageNodeData, VideoNodeData } from '@/types'
import type { NodeChange, EdgeChange, Connection } from '@xyflow/react'
import { applyNodeChanges, applyEdgeChanges } from '@xyflow/react'
import { v4 as uuid } from 'uuid'

interface NodeStoreState {
  nodes: AppNode[]
  edges: AppEdge[]

  // React Flow 事件处理
  onNodesChange: (changes: NodeChange[]) => void
  onEdgesChange: (changes: EdgeChange[]) => void

  // 节点 CRUD
  addImageNode: (data: Omit<ImageNodeData, 'nodeType' | 'status' | 'result' | 'assetRefs'> & { assetRefs?: string[]; result?: ImageNodeData['result'] }, position?: { x: number; y: number }) => AppNode
  addVideoNode: (data: Omit<VideoNodeData, 'nodeType' | 'status' | 'result' | 'tailFrame' | 'previousFrameRef' | 'order' | 'duration'> & { order?: number; duration?: number }, position?: { x: number; y: number }) => AppNode
  updateNodeData: (nodeId: string, data: Partial<AppNode['data']>) => void
  removeNode: (nodeId: string) => void
  setNodeStatus: (nodeId: string, status: NodeStatus) => void

  // 边管理
  addEdge: (connection: Connection) => void
  removeEdge: (edgeId: string) => void

  // 尾帧继承
  propagateTailFrame: (fromNodeId: string, toNodeId: string) => void

  // 批量操作
  loadNodes: (nodes: AppNode[], edges: AppEdge[]) => void
  clearAll: () => void
}

export const useNodeStore = create<NodeStoreState>((set, get) => ({
  nodes: [],
  edges: [],

  onNodesChange: (changes) =>
    set({ nodes: applyNodeChanges(changes, get().nodes) as AppNode[] }),

  onEdgesChange: (changes) =>
    set({ edges: applyEdgeChanges(changes, get().edges) as AppEdge[] }),

  addImageNode: (data, position) => {
    const node: AppNode = {
      id: uuid(),
      type: 'imageNode',
      position: position ?? { x: 250, y: 100 },
      data: {
        ...data,
        nodeType: 'image' as const,
        status: 'pending' as NodeStatus,
        result: data.result ?? null,
        assetRefs: data.assetRefs ?? [],
      },
    }
    set((s) => ({ nodes: [...s.nodes, node] }))
    return node
  },

  addVideoNode: (data, position) => {
    const defaults = get().nodes.filter((n) => n.type === 'videoNode').length
    const node: AppNode = {
      id: uuid(),
      type: 'videoNode',
      position: position ?? { x: 250, y: 100 + defaults * 200 },
      data: {
        ...data,
        nodeType: 'video' as const,
        status: 'pending' as NodeStatus,
        result: null,
        tailFrame: null,
        previousFrameRef: data.previousFrameRef ?? null,
        order: data.order ?? defaults + 1,
        duration: data.duration ?? 15,
      },
    }
    set((s) => ({ nodes: [...s.nodes, node] }))
    return node
  },

  updateNodeData: (nodeId, data) =>
    set((s) => ({
      nodes: s.nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...data } as AppNode['data'] } : n
      ),
    })),

  removeNode: (nodeId) =>
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== nodeId),
      edges: s.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
    })),

  setNodeStatus: (nodeId, status) =>
    set((s) => ({
      nodes: s.nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, status } as AppNode['data'] } : n
      ),
    })),

  addEdge: (connection) => {
    if (!connection.source || !connection.target) return
    // 避免重复边
    const exists = get().edges.some(
      (e) => e.source === connection.source && e.target === connection.target
    )
    if (exists) return
    const edge: AppEdge = {
      id: uuid(),
      source: connection.source,
      target: connection.target,
      sourceHandle: connection.sourceHandle ?? undefined,
      targetHandle: connection.targetHandle ?? undefined,
      data: { edgeType: 'data_flow' },
      animated: true,
    }
    set((s) => ({ edges: [...s.edges, edge] }))
  },

  removeEdge: (edgeId) =>
    set((s) => ({ edges: s.edges.filter((e) => e.id !== edgeId) })),

  propagateTailFrame: (fromNodeId, toNodeId) => {
    const fromNode = get().nodes.find((n) => n.id === fromNodeId)
    if (!fromNode || fromNode.type !== 'videoNode') return
    const tailFrame = (fromNode.data as VideoNodeData).tailFrame
    if (!tailFrame) return

    set((s) => ({
      nodes: s.nodes.map((n) => {
        if (n.id === toNodeId && n.type === 'videoNode') {
          return {
            ...n,
            data: {
              ...n.data,
              previousFrameRef: fromNodeId,
            } as VideoNodeData,
          }
        }
        return n
      }),
      edges: [
        ...s.edges,
        {
          id: uuid(),
          source: fromNodeId,
          target: toNodeId,
          data: { edgeType: 'frame_continuity', label: '尾帧继承' },
          animated: true,
          style: { stroke: '#f59e0b', strokeDasharray: '5,5' },
        },
      ],
    }))
  },

  loadNodes: (nodes, edges) => set({ nodes, edges }),
  clearAll: () => set({ nodes: [], edges: [] }),
}))
