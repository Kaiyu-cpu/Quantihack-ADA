import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function EDA() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.edaPolymarket()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) {
    return <div className="card">Error: {error}</div>
  }

  return (
    <div className="grid">
      <div className="card">
        <h3>Dataset Overview</h3>
        <p>Confirm ranges, strike counts, and data freshness before modeling.</p>
        <ul>
          <li>Polymarket rows: {data?.rows ?? '—'}</li>
          <li>Strikes: {data?.strikes ?? '—'}</li>
          <li>Date range: {data ? `${data.range_start} → ${data.range_end}` : '—'}</li>
        </ul>
      </div>
      <div className="card">
        <h3>Liquidity Snapshot</h3>
        <p>Pick the most liquid strike to avoid noisy signals.</p>
        <div className="panel-row">
          <span className="badge">Strike ${data?.top_strike ?? '—'}</span>
          <span className="badge">Direction: {data?.top_direction ?? '—'}</span>
        </div>
      </div>
      <div className="card">
        <h3>News & Reddit Activity</h3>
        <p>Use volume spikes to spot narrative shifts.</p>
        <div className="panel-row">
          <span className="badge">News: {data?.news_count ?? 0}</span>
          <span className="badge">Reddit: {data?.reddit_count ?? 0}</span>
        </div>
      </div>
    </div>
  )
}
