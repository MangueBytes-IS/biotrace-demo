export default function ProgressBar({ value, label }: { value: number; label?: string }) {
  const percent = Math.max(0, Math.min(100, Math.round(value)))
  return (
    <div className="progress">
      <div className="progress__meta">
        <span>{label || 'Processando'}</span>
        <span className="progress__value">{percent}%</span>
      </div>
      <div
        className="progress__track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={label || 'Progresso da análise'}
      >
        <div className="progress__fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}
