export type Stage = 'queued' | 'decoding' | 'separating' | 'melody' | 'chords' | 'rendering' | 'done'

export interface JobStatus {
  id: string
  title: string
  filename: string | null
  status: 'queued' | 'started' | 'deferred' | 'scheduled' | 'finished' | 'failed' | 'stopped' | 'canceled'
  stage: Stage
  stage_progress: number
  progress: number
  error: string | null
}

export interface Score {
  title: string
  duration: number
  key: string
  tempo: number
  chords: { start: number; end: number; name: string; notes: number[] }[]
  melody: { start: number; end: number; pitch: number; name: string }[]
}

export type OutputFile = 'video.mp4' | 'melody.mid' | 'chords.mid' | 'notes.json'

export const ACCEPT = '.mp3,.wav,.m4a,.flac,.ogg,.aac,audio/*'
export const MAX_UPLOAD_MB = 100
export const MAX_DURATION_S = 15 * 60

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // fall through
  }
  return `Request failed (${res.status})`
}

/** Upload with progress reporting (fetch can't report upload progress). */
export function uploadSong(file: File, onProgress: (fraction: number) => void): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/jobs')
    xhr.responseType = 'json'
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      if (xhr.status === 201) resolve(xhr.response.id)
      else reject(new Error(xhr.response?.detail ?? `Upload failed (${xhr.status})`))
    }
    xhr.onerror = () => reject(new Error('Upload failed. Check your connection and try again.'))
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
}

export async function getJob(id: string): Promise<JobStatus> {
  const res = await fetch(`/api/jobs/${id}`)
  if (!res.ok) throw new Error(await errorMessage(res))
  return res.json()
}

export async function getScore(id: string): Promise<Score> {
  const res = await fetch(fileUrl(id, 'notes.json'))
  if (!res.ok) throw new Error(await errorMessage(res))
  return res.json()
}

export function fileUrl(id: string, name: OutputFile, download = false): string {
  return `/api/jobs/${id}/files/${name}${download ? '?download=1' : ''}`
}

export function formatTime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** Read an audio file's duration in the browser, or null if it can't be decoded. */
export function audioDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const audio = new Audio()
    audio.preload = 'metadata'
    const done = (value: number | null) => {
      URL.revokeObjectURL(url)
      resolve(value)
    }
    audio.onloadedmetadata = () => done(Number.isFinite(audio.duration) ? audio.duration : null)
    audio.onerror = () => done(null)
    audio.src = url
  })
}
