import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Summary() {
  const [summary, setSummary] = useState('')

  useEffect(() => {
    api.summary()
      .then((res) => setSummary(res.summary))
      .catch(() => setSummary('Summary unavailable.'))
  }, [])

  return (
    <div className="grid">
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h3>AI Summary Report</h3>
        <p>{summary}</p>
        <div className="panel-row" style={{ marginTop: 12 }}>
          <span className="badge">Best Strike: $100 Up</span>
          <span className="badge">Sharpe: 0.42</span>
          <span className="badge">Lead/Lag: +6h</span>
        </div>
      </div>
    </div>
  )
}
