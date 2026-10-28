import type { JobStatus, Stage } from '../api'

const STEPS: { stages: Stage[]; title: string; detail: string }[] = [
  { stages: ['queued', 'decoding', 'separating'], title: 'Separating vocals', detail: 'Splitting the voice from the instruments' },
  { stages: ['melody'], title: 'Transcribing melody', detail: 'Turning the sung line into notes' },
  { stages: ['chords'], title: 'Detecting chords', detail: 'Matching harmony beat by beat' },
  { stages: ['rendering'], title: 'Rendering video', detail: 'Drawing falling notes at 1080p, 30 fps' },
]

export function ProgressSteps({ job }: { job: JobStatus }) {
  const activeIndex = job.stage === 'done' ? STEPS.length : STEPS.findIndex((s) => s.stages.includes(job.stage))
  const stagePct = job.stage === 'separating' ? Math.round(job.stage_progress * 100) : null
  const renderPct = job.stage === 'rendering' ? Math.round(job.stage_progress * 100) : null

  return (
    <ol className="step-list">
      {STEPS.map((step, i) => {
        const done = i < activeIndex
        const active = i === activeIndex
        const pct = active ? (stagePct ?? renderPct) : null
        const status = done ? 'Done' : active ? (job.stage === 'queued' ? 'Queued' : pct !== null ? `${pct}%` : 'Working') : 'Waiting'
        return (
          <li key={step.title} className={`step${done ? ' step--done' : ''}${active ? ' step--active' : ''}`}
            aria-current={active ? 'step' : undefined}>
            <span className="step__dot">
              {done ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0B0D10" strokeWidth="3"
                  strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M5 12l5 5L20 7" />
                </svg>
              ) : (
                i + 1
              )}
            </span>
            <span className="step__body">
              <span className="step__title">{step.title}</span>
              <span className="step__detail">{step.detail}</span>
              {active && pct !== null && (
                <span className="bar bar--thin">
                  <span className="bar__fill" style={{ display: 'block', width: `${pct}%` }} />
                </span>
              )}
            </span>
            <span className="step__status">{status}</span>
          </li>
        )
      })}
    </ol>
  )
}
