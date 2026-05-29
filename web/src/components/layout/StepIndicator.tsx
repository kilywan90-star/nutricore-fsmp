// ============================================================
// D2: 步骤指示器
// ============================================================

export type Step = 'character' | 'scene' | 'video'

interface Props {
  current: Step
  onChange: (step: Step) => void
}

const steps: { key: Step; label: string; desc: string }[] = [
  { key: 'character', label: '第一步', desc: '固定角色' },
  { key: 'scene', label: '第二步', desc: '固定场景' },
  { key: 'video', label: '第三步', desc: '情节连续' },
]

export function StepIndicator({ current, onChange }: Props) {
  return (
    <div className="flex items-center gap-2 px-4">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center">
          <button
            onClick={() => onChange(s.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all text-sm
              ${current === s.key
                ? 'bg-accent-primary text-white shadow-lg'
                : 'bg-panel-bg text-text-secondary hover:text-text-primary hover:bg-canvas-border'
              }`}
          >
            <span className="font-bold">{s.label}</span>
            <span className="hidden sm:inline">{s.desc}</span>
          </button>
          {i < steps.length - 1 && (
            <div className="w-6 h-px bg-canvas-border mx-1" />
          )}
        </div>
      ))}
    </div>
  )
}
