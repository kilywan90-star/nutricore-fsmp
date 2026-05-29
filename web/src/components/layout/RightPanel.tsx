// ============================================================
// D4: 右侧属性面板
// ============================================================

import type { AppNode, AppNodeData } from '@/types'
import { useNodeStore } from '@/stores/nodeStore'

interface Props {
  selectedNode: AppNode | null
}

export function RightPanel({ selectedNode }: Props) {
  if (!selectedNode) {
    return (
      <div className="w-72 h-full bg-panel-bg border-l border-panel-border flex items-center justify-center">
        <p className="text-text-secondary text-sm px-4 text-center">
          选择一个节点查看属性
        </p>
      </div>
    )
  }

  const data = selectedNode.data as AppNodeData

  return (
    <div className="w-72 h-full bg-panel-bg border-l border-panel-border overflow-y-auto">
      <div className="px-4 py-3 border-b border-panel-border">
        <h3 className="text-sm font-semibold text-text-primary">{data.label}</h3>
        <p className="text-xs text-text-secondary mt-1">
          {data.nodeType === 'image' ? '图片节点' : '视频节点'}
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* 状态 */}
        <div>
          <label className="text-xs text-text-secondary block mb-1">状态</label>
          <StatusBadge status={data.status} />
        </div>

        {/* 模型 */}
        {'model' in data && (
          <div>
            <label className="text-xs text-text-secondary block mb-1">模型</label>
            <p className="text-sm text-text-primary">{data.model}</p>
          </div>
        )}

        {/* 提示词 */}
        {'prompt' in data && (
          <div>
            <label className="text-xs text-text-secondary block mb-1">提示词</label>
            <p className="text-xs text-text-primary bg-canvas-bg rounded p-2 max-h-32 overflow-y-auto">
              {data.prompt}
            </p>
          </div>
        )}

        {/* 分镜脚本 */}
        {'shotScript' in data && (
          <div>
            <label className="text-xs text-text-secondary block mb-1">分镜脚本</label>
            <p className="text-xs text-text-primary bg-canvas-bg rounded p-2 max-h-32 overflow-y-auto">
              {data.shotScript || '(未设置)'}
            </p>
          </div>
        )}

        {/* 生成结果 */}
        {'result' in data && data.result && (
          <div>
            <label className="text-xs text-text-secondary block mb-1">生成结果</label>
            <img
              src={data.result.thumbnailUrl}
              alt="Result"
              className="w-full rounded-lg border border-canvas-border"
            />
          </div>
        )}

        {/* 尾帧 */}
        {'tailFrame' in data && (data as { tailFrame: { thumbnailUrl: string } | null }).tailFrame && (
          <div>
            <label className="text-xs text-text-secondary block mb-1">尾帧</label>
            <img
              src={(data as { tailFrame: { thumbnailUrl: string } }).tailFrame.thumbnailUrl}
              alt="Tail Frame"
              className="w-full rounded-lg border border-warning/50"
            />
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-gray-600 text-gray-200',
    queued: 'bg-blue-600 text-blue-100',
    running: 'bg-yellow-600 text-yellow-100 animate-pulse',
    completed: 'bg-green-600 text-green-100',
    failed: 'bg-red-600 text-red-100',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? ''}`}>
      {status}
    </span>
  )
}
