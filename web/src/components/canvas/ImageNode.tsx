// ============================================================
// E1: 图片节点 (React Flow 自定义节点)
// ============================================================

import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { ImageNodeData } from '@/types'

export function ImageNodeComponent({ data, selected }: NodeProps) {
  const d = data as ImageNodeData
  const purposeLabel =
    d.purpose === 'character' ? '角色' : d.purpose === 'scene' ? '场景' : '风格化'

  return (
    <div
      className={`bg-panel-bg border-2 rounded-xl w-56 transition-all
        ${selected ? 'border-accent-primary shadow-lg shadow-accent-primary/20' : 'border-canvas-border'}
        ${d.status === 'running' ? 'animate-pulse border-yellow-500' : ''}
        ${d.status === 'failed' ? 'border-error' : ''}
      `}
    >
      {/* 顶部标签 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-canvas-border">
        <span className="text-xs font-semibold text-accent-secondary">{purposeLabel}</span>
        <StatusDot status={d.status} />
      </div>

      {/* 内容 */}
      <div className="p-3">
        <p className="text-sm text-text-primary font-medium truncate">{d.label}</p>
        <p className="text-xs text-text-secondary mt-1 line-clamp-2">{d.description || d.prompt}</p>

        {d.result && (
          <div className="mt-2">
            <img
              src={d.result.thumbnailUrl}
              alt={d.label}
              className="w-full h-24 object-cover rounded-lg border border-canvas-border"
            />
          </div>
        )}

        {!d.result && d.status === 'pending' && (
          <div className="mt-2 h-24 rounded-lg border border-dashed border-canvas-border
            flex items-center justify-center text-xs text-text-secondary">
            待生成
          </div>
        )}

        {d.status === 'running' && !d.result && (
          <div className="mt-2 h-24 rounded-lg bg-accent-primary/10
            flex items-center justify-center text-xs text-accent-secondary">
            生成中...
          </div>
        )}
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-accent-secondary !w-3 !h-3"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-accent-secondary !w-3 !h-3"
      />
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-gray-500',
    queued: 'bg-blue-500',
    running: 'bg-yellow-500 animate-pulse',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  }
  return <div className={`w-2 h-2 rounded-full ${colors[status] ?? ''}`} />
}
