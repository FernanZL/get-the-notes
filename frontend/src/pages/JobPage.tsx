import { useEffect, useState } from 'react'
import { getJob, type JobStatus } from '../api'
import { Header } from '../components/Header'
import { ProgressSteps } from '../components/ProgressSteps'
import { ResultView } from './ResultView'

const POLL_MS = 2000

export function JobPage({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<JobStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let timer: number | undefined
    let cancelled = false
    async function poll() {
      try {
        const next = await getJob(jobId)
        if (cancelled) return
        setJob(next)
        setError(null)
        if (next.status === 'finished' || next.status === 'failed') return
      } catch (err) {
        if (cancelled) return
        setError((err as Error).message)
      }
      timer = window.setTimeout(poll, POLL_MS)
    }
    poll()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [jobId])

  const finished = job?.status === 'finished'
  const failed = job?.status === 'failed' || job?.status === 'stopped' || job?.status === 'canceled'

  return (
    <>
      <Header>
        {(finished || failed) && <a href="#/" className="btn btn--secondary btn--small">New song</a>}
      </Header>
      {finished && job ? (
        <ResultView job={job} />
      ) : (
        <main className="main main--narrow">
          <section className="stack">
            <p className="eyebrow">{failed ? 'Something went wrong' : 'Working on it'}</p>
            <h1 className="page-title">{failed ? 'We couldn’t finish this song' : 'Building your tutorial'}</h1>
            {job && <p className="note filename" style={{ color: 'var(--text-2)' }}>{job.filename ?? job.title}</p>}
          </section>

          {failed && job ? (
            <>
              <p className="error" role="alert">{job.error}</p>
              <a href="#/" className="btn btn--primary" style={{ alignSelf: 'flex-start' }}>Try another song</a>
            </>
          ) : (
            <>
              <section aria-label="Overall progress" className="stack" style={{ gap: 10 }}>
                <div className="progress-head">
                  <span>Overall</span>
                  <strong>{Math.round((job?.progress ?? 0) * 100)}%</strong>
                </div>
                <div className="bar" role="progressbar" aria-valuemin={0} aria-valuemax={100}
                  aria-valuenow={Math.round((job?.progress ?? 0) * 100)}>
                  <div className="bar__fill" style={{ width: `${(job?.progress ?? 0) * 100}%` }} />
                </div>
              </section>
              {job && <ProgressSteps job={job} />}
              {error && <p className="error" role="alert">{error}</p>}
              <p className="note">Keep this tab open — the video appears here when it is ready. You can also bookmark this page and come back later.</p>
            </>
          )}
        </main>
      )}
    </>
  )
}
