import { useState } from 'react'
import { api } from '../api.js'

const sources = [
  {
    name: 'Polymarket Prices',
    description: 'Fetch YES-token prices for an event slug and persist CSV.',
    command: 'python ingestion/polymarket_fetcher.py',
    action: (slug) => api.fetchPolymarket({ event_slug: slug })
  },
  {
    name: 'News Headlines',
    description: 'Pull recent headlines via Yahoo Finance tickers.',
    command: 'python ingestion/news_fetcher.py',
    action: (topic) => api.fetchNews({ topic })
  },
  {
    name: 'Reddit Posts',
    description: 'Collect subreddit posts via Reddit public JSON API.',
    command: 'python ingestion/reddit_fetcher.py',
    action: (payload) => api.fetchReddit(payload)
  },
  {
    name: 'GitHub Issues',
    description: 'Fetch issue history for repo health / survival analysis.',
    command: 'python ingestion/github_fetcher.py',
    action: () => api.fetchGithub()
  }
]

export default function FetchData() {
  const [status, setStatus] = useState({})
  const [eventSlug, setEventSlug] = useState('will-crude-oil-cl-hit-by-end-of-march')
  const [topic, setTopic] = useState('oil')
  const [fastReddit, setFastReddit] = useState(true)

  async function runFetch(source) {
    try {
      setStatus((s) => ({ ...s, [source.name]: 'Running...' }))
      let result
      if (source.name === 'Polymarket Prices') result = await source.action(eventSlug)
      else if (source.name === 'GitHub Issues') result = await source.action()
      else if (source.name === 'Reddit Posts') result = await source.action({ topic, fast: fastReddit })
      else result = await source.action(topic)
      const msg = result.error ? `Error: ${result.error}` : `OK (${result.rows ?? 'done'})`
      setStatus((s) => ({ ...s, [source.name]: msg }))
    } catch (err) {
      setStatus((s) => ({ ...s, [source.name]: `Error: ${err.message}` }))
    }
  }

  return (
    <div className="grid">
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h3>Fetch Configuration</h3>
        <div className="panel-row">
          <input
            className="input"
            value={eventSlug}
            onChange={(e) => setEventSlug(e.target.value)}
            placeholder="Polymarket event slug"
          />
          <input
            className="input"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Topic (oil, crypto, gold)"
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={fastReddit} onChange={(e) => setFastReddit(e.target.checked)} />
            Fast Reddit
          </label>
        </div>
      </div>
      {sources.map((source) => (
        <div className="card" key={source.name}>
          <h3>{source.name}</h3>
          <p>{source.description}</p>
          <div className="badge">Local Script</div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, opacity: 0.8 }}>
              {source.command}
            </div>
            <button className="button" style={{ marginTop: 12 }} onClick={() => runFetch(source)}>
              Run Fetch
            </button>
            <div style={{ marginTop: 10, color: 'var(--muted)' }}>
              {status[source.name] || 'Idle'}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
