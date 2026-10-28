import { useEffect, useRef, useState } from 'react'
import { fileUrl, formatTime, getScore, type JobStatus, type Score } from '../api'

export function ResultView({ job }: { job: JobStatus }) {
  const video = useRef<HTMLVideoElement>(null)
  const [score, setScore] = useState<Score | null>(null)
  const [time, setTime] = useState(0)

  useEffect(() => {
    getScore(job.id).then(setScore, () => setScore(null))
  }, [job.id])

  const current = score?.chords.findIndex((c) => c.start <= time && time < c.end) ?? -1

  function seek(t: number) {
    if (!video.current) return
    video.current.currentTime = t
    video.current.play()
  }

  return (
    <main className="main main--result">
      <section className="stack" style={{ gap: 8 }}>
        <p className="eyebrow eyebrow--ready">Ready</p>
        <h1 className="page-title">{job.title}</h1>
      </section>

      <div className="result-layout">
        <section className="player" aria-label="Tutorial video">
          <video
            ref={video}
            src={fileUrl(job.id, 'video.mp4')}
            controls
            preload="metadata"
            onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
          />
        </section>

        <aside className="sidebar">
          <section className="panel">
            <h2>Downloads</h2>
            <a className="download download--primary" href={fileUrl(job.id, 'video.mp4', true)}>
              Video <span className="download__fmt">MP4</span>
            </a>
            <a className="download" href={fileUrl(job.id, 'melody.mid', true)}>
              <span className="download__label"><i className="swatch" style={{ background: 'var(--amber)' }} />Melody</span>
              <span className="download__fmt">MIDI</span>
            </a>
            <a className="download" href={fileUrl(job.id, 'chords.mid', true)}>
              <span className="download__label"><i className="swatch" style={{ background: 'var(--teal)' }} />Chords</span>
              <span className="download__fmt">MIDI</span>
            </a>
            <a className="download" href={fileUrl(job.id, 'notes.json', true)}>
              All notes <span className="download__fmt">JSON</span>
            </a>
          </section>
          {score && (
            <section className="stats">
              <div className="stat">
                <span className="stat__label">Key</span>
                <span className="stat__value">{score.key}</span>
              </div>
              <div className="stat">
                <span className="stat__label">Tempo</span>
                <span className="stat__value">{score.tempo ? `${Math.round(score.tempo)} BPM` : '—'}</span>
              </div>
            </section>
          )}
        </aside>
      </div>

      {score && score.chords.length > 0 && (
        <section className="stack" style={{ gap: 14 }}>
          <h2 style={{ margin: 0, fontSize: 20 }}>Chord progression</h2>
          <div className="chords">
            {score.chords.map((c, i) => (
              <button
                type="button"
                key={i}
                className={`chord${i === current ? ' chord--current' : ''}`}
                onClick={() => seek(c.start)}
                aria-label={`${c.name} at ${formatTime(c.start)}, play from here`}
              >
                {c.name}
                <span className="chord__time">{formatTime(c.start)}</span>
              </button>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
