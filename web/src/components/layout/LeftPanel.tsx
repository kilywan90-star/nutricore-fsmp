// ============================================================
// D3: 左侧面板 — 资产库 / 脚本
// ============================================================

import type { Step } from './StepIndicator'
import { CharacterPanel } from '@/components/character/CharacterPanel'
import { ScenePanel } from '@/components/scene/ScenePanel'
import { ScriptPanel } from '@/components/video/ScriptPanel'

interface Props {
  step: Step
}

export function LeftPanel({ step }: Props) {
  return (
    <div className="w-80 h-full bg-panel-bg border-r border-panel-border flex flex-col overflow-hidden">
      <div className="px-4 py-3 border-b border-panel-border">
        <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
          {step === 'character' && '角色资产库'}
          {step === 'scene' && '场景资产库'}
          {step === 'video' && '脚本 & 分镜'}
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto">
        {step === 'character' && <CharacterPanel />}
        {step === 'scene' && <ScenePanel />}
        {step === 'video' && <ScriptPanel />}
      </div>
    </div>
  )
}
