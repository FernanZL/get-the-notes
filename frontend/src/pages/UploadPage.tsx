import { useRef, useState, type DragEvent } from 'react'
import { ACCEPT, MAX_DURATION_S, MAX_UPLOAD_MB, audioDuration, formatTime, uploadSong } from '../api'
import { Header } from '../components/Header'

const KEY_PATTERN = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]
const LIT: Record<number, string> = { 9: '#1FB5A3', 12: '#1FB5A3', 16: '#1FB5A3', 30: '#FFB547', 33: '#FFB547' }
const DECOR_KEYS = Array.from({ length: 42 }, (_, i) => {
  const black = KEY_PATTERN[i % 12] === 1
  return { height: black ? 36 : 56, background: LIT[i] ?? (black ? '#2A2F38' : '#3A404B') }
})

const HOW_IT_WORKS = [
  ['Separate', 'The vocals are split from the band so each part can be transcribed on its own.'],
  ['Transcribe the melody', 'The sung line becomes single notes placed around middle C for your right hand.'],
  ['Find the chords', 'Chords are detected beat by beat and voiced low on the keyboard for your left hand.'],
  ['Render the video', 'Falling notes and labels with a piano playing the transcription, so you can check every note by ear.'],
]

interface Picked {
  file: File
  duration: number | null
}

function formatSize(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function UploadPage({ onUploaded }: { onUploaded: (jobId: string) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [picked, setPicked] = useState<Picked | null>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function pick(file: File | undefined) {
    if (!file) return
    setError(null)
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`Files can be at most ${MAX_UPLOAD_MB} MB.`)
      return
    }
    const duration = await audioDuration(file)
    if (duration !== null && duration > MAX_DURATION_S) {
      setError(`Songs can be at most ${MAX_DURATION_S / 60} minutes long.`)
      return
    }
    setPicked({ file, duration })
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    pick(e.dataTransfer.files[0])
  }

  async function submit() {
    if (!picked) return
    setError(null)
    setUploading(0)
    try {
      onUploaded(await uploadSong(picked.file, setUploading))
    } catch (err) {
      setError((err as Error).message)
      setUploading(null)
    }
  }

  const zoneClass = ['dropzone', dragging && 'dropzone--active', picked && 'dropzone--picked']
    .filter(Boolean)
    .join(' ')

  return (
    <>
      <Header>
        <nav>
          <a href="#how" className="nav-link" onClick={(e) => {
            e.preventDefault()
            document.getElementById('how')?.scrollIntoView({ behavior: 'smooth' })
          }}>
            How it works
          </a>
        </nav>
      </Header>
      <main className="main main--wide">
        <section className="hero">
          <p className="eyebrow">Song → piano tutorial</p>
          <h1>
            Upload a song.
            <br />
            Get the notes.
          </h1>
          <p className="lede">
            We separate the vocals, find the chords and render a falling-notes video — chords in your{' '}
            <span className="lh">left hand</span>, the sung melody in your <span className="rh">right hand</span>.
          </p>
        </section>

        <section aria-label="Upload a song" className="stack" style={{ gap: 16 }}>
          <div
            className={zoneClass}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div className="dropzone__keys" aria-hidden="true">
              {DECOR_KEYS.map((k, i) => (
                <span key={i} style={k} />
              ))}
            </div>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#E8EAED" strokeWidth="1.6"
              strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 18V5l12-2v13" />
              <circle cx="6" cy="18" r="3" />
              <circle cx="18" cy="16" r="3" />
            </svg>
            <input
              ref={input}
              type="file"
              accept={ACCEPT}
              hidden
              onChange={(e) => {
                pick(e.target.files?.[0])
                e.target.value = ''
              }}
            />
            {!picked ? (
              <>
                <p className="dropzone__title">Drop a song here</p>
                <p className="dropzone__hint">MP3, WAV, M4A or FLAC · up to 15 minutes · {MAX_UPLOAD_MB} MB</p>
                <button type="button" className="btn btn--secondary" onClick={() => input.current?.click()}>
                  Choose a file
                </button>
              </>
            ) : (
              <>
                <div className="file-chip">
                  <span className="filename">{picked.file.name}</span>
                  <span className="file-chip__meta">
                    {picked.duration !== null && `${formatTime(picked.duration)} · `}
                    {formatSize(picked.file.size)}
                  </span>
                  <button type="button" className="icon-btn" aria-label="Remove file"
                    disabled={uploading !== null} onClick={() => setPicked(null)}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                      strokeLinecap="round" aria-hidden="true">
                      <path d="M18 6 6 18M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <button type="button" className="btn btn--primary" onClick={submit} disabled={uploading !== null}>
                  {uploading === null ? 'Make my tutorial' : `Uploading… ${Math.round(uploading * 100)}%`}
                  {uploading === null && (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"
                      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M5 12h14M13 6l6 6-6 6" />
                    </svg>
                  )}
                </button>
              </>
            )}
          </div>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="legend">
            <span><i className="swatch" style={{ background: 'var(--teal)' }} />Left hand — chords</span>
            <span><i className="swatch" style={{ background: 'var(--amber)' }} />Right hand — vocal melody</span>
            <span>A 3–4 minute song takes a few minutes to process.</span>
          </div>
        </section>

        <section id="how" className="stack" style={{ gap: 24 }}>
          <h2 className="section-title">How it works</h2>
          <div className="steps-grid">
            {HOW_IT_WORKS.map(([title, text], i) => (
              <div className="card" key={title}>
                <span className="card__num">{String(i + 1).padStart(2, '0')}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
    </>
  )
}
