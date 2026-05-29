// ============================================================
// E2: 视频节点 (React Flow 自定义节点)
// ============================================================

import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { VideoNodeData } from '@/types'

export function VideoNodeComponent({ data, selected }: NodeProps) {
  const d = data as VideoNodeData

  return (
    <div
      className={`bg-panel-bg border-2 rounded-xl w-64 transition-all
        ${selected ? 'border-accent-primary shadow-lg shadow-accent-primary/20' : 'border-canvas-border'}
        ${d.status === 'running' ? 'border-yellow-500' : ''}
        ${d.status === 'failed' ? 'border-error' : ''}
      `}
    >
      {/* 顶部 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-canvas-border">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-warning">#{d.order}</span>
          <span className="text-xs font-semibold text-text-primary">视频分镜</span>
        </div>
        <StatusBadge status={d.status} />
      </div>

      {/* 内容 */}
      <div className="p-3">
        <p className="text-sm text-text-primary font-medium truncate">{d.label}</p>
        <p className="text-xs text-text-secondary mt-1 line-clamp-2">
          {d.shotScript || '(点击编辑分镜脚本)'}
        </p>

        {/* 引用信息 */}
        <div className="flex gap-2 mt-2 text-[10px] text-text-secondary">
          <span className="bg-accent-primary/10 px-1.5 py-0.5 rounded">
            {d.characterRef ? '已绑定角色' : '未绑定角色'}
          </span>
          <span className="bg-accent-primary/10 px-1.5 py-0.5 rounded">
            {d.sceneRef ? '已绑定场景' : '未绑定场景'}
          </span>
        </div>

        {/* 尾帧引用 */}
        {d.previousFrameRef && (
          <div className="mt-2 text-[10px] text-warning flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-warning" />
            继承上级尾帧
          </div>
        )}

        {/* 生成结果 */}
        {d.result && (
          <div className="mt-2">
            <img
              src={d.result.thumbnailUrl}
              alt={d.label}
              className="w-full h-20 object-cover rounded-lg border border-canvas-border"
            />
            <p className="text-[10px] text-text-secondary mt-1 text-right">
              {d.duration}s
            </p>
          </div>
        )}

        {!d.result && d.status === 'pending' && (
          <div className="mt-2 h-20 rounded-lg border border-dashed border-canvas-border
            flex items-center justify-center text-xs text-text-secondary">
            待生成视频
          </div>
        )}
      </div>

      {/* 尾帧输出指示 */}
      {d.tailFrame && (
        <div className="px-3 pb-2">
          <div className="text-[10px] text-warning flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-warning" />
            尾帧已就绪，可传递
          </div>
        </div>
      )}

      <Handle type="target" position={Position.Top} className="!bg-warning !w-3 !h-3" />
      <Handle type="source" position={Position.Bottom} className="!bg-warning !w-3 !h-3" />
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-gray-600 text-gray-200',
    queued: 'bg-blue-600 text-blue-100',
    running: 'bg-yellow-600 text-yellow-100',
    completed: 'bg-green-600 text-green-100',
    failed: 'bg-red-600 text-red-100',
  }
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded ${colors[status] ?? ''}`}>
      {status}
    </span>
  )
}
