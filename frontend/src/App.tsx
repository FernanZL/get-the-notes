import { useEffect, useState } from 'react'
import { JobPage } from './pages/JobPage'
import { UploadPage } from './pages/UploadPage'

function jobIdFromHash(): string | null {
  const match = window.location.hash.match(/^#\/job\/([0-9a-f]{32})$/)
  return match ? match[1] : null
}

export default function App() {
  const [jobId, setJobId] = useState(jobIdFromHash)

  useEffect(() => {
    const onHash = () => {
      setJobId(jobIdFromHash())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <div className="app">
      {jobId ? (
        <JobPage key={jobId} jobId={jobId} />
      ) : (
        <UploadPage onUploaded={(id) => (window.location.hash = `#/job/${id}`)} />
      )}
    </div>
  )
}
