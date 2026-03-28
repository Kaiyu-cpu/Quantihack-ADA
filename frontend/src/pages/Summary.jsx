import { useState, useCallback } from 'react'

const API = 'http://localhost:8000'

const TOPICS = [
  { id: 'oil',    label: 'Crude Oil',  icon: '🛢️' },
  { id: 'crypto', label: 'Crypto',     icon: '₿' },
  { id: 'gold',   label: 'Gold',       icon: '🥇' },
]

const SENTIMENT_COLOR = {
  bullish: '#00f5d4',
  bearish: '#ff6b6b',
  neutral: '#ffb703',
}

function sentimentFromText(text) {
  const lower = (text || '').toLowerCase()
  if (lower.includes('bullish')) return 'bullish'
  if (lower.includes('bearish')) return 'bearish'
  return 'neutral'
}

function NewsCard({ item }) {
  return (
    <div style={{
      background: 'var(--panel-2)',
      borderRadius: 12,
      padding: '12px 14px',
      borderLeft: '3px solid var(--accent)',
      marginBottom: 10,
    }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>
        {item.published_utc?.slice(0, 10)} · {item.source}
      </div>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, lineHeight: 1.4 }}>
        <a href={item.url} target="_blank" rel="noreferrer"
          style={{ color: 'var(--text)', textDecoration: 'none' }}
          onMouseOver={e => e.target.style.color = 'var(--accent)'}
          onMouseOut={e => e.target.style.color = 'var(--text)'}
        >
          {item.title}
        </a>
      </div>
      {item.summary && (
        <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>
          {item.summary.slice(0, 160)}{item.summary.length > 160 ? '…' : ''}
        </div>
      )}
    </div>
  )
}

function RedditCard({ item }) {
  return (
    <div style={{
      background: 'var(--panel-2)',
      borderRadius: 12,
      padding: '12px 14px',
      borderLeft: '3px solid var(--accent-2)',
      marginBottom: 10,
    }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 4 }}>
        r/{item.subreddit} · {item.published_utc?.slice(0, 10)}
        <span style={{ marginLeft: 8, color: '#00f5d4' }}>↑{item.score}</span>
        <span style={{ marginLeft: 6, color: 'var(--muted)' }}>💬{item.num_comments}</span>
      </div>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, lineHeight: 1.4 }}>
        <a href={item.permalink} target="_blank" rel="noreferrer"
          style={{ color: 'var(--text)', textDecoration: 'none' }}
          onMouseOver={e => e.target.style.color = 'var(--accent-2)'}
          onMouseOut={e => e.target.style.color = 'var(--text)'}
        >
          {item.title}
        </a>
      </div>
      {item.selftext && (
        <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>
          {item.selftext.slice(0, 140)}{item.selftext.length > 140 ? '…' : ''}
        </div>
      )}
    </div>
  )
}

function AISummaryDisplay({ summary, model, newsCount, redditCount }) {
  const sentiment = sentimentFromText(summary)
  const color = SENTIMENT_COLOR[sentiment]

  const sections = summary
    .split(/\n(?=###\s)/)
    .map(s => s.trim())
    .filter(Boolean)

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
        <span className="badge" style={{ background: `${color}22`, color }}>
          {sentiment.toUpperCase()} SENTIMENT
        </span>
        <span className="badge">Model: {model}</span>
        <span className="badge">{newsCount} news · {redditCount} reddit</span>
      </div>

      {sections.length > 1 ? (
        sections.map((section, i) => {
          const headingMatch = section.match(/^###\s(.+)\n/)
          const heading = headingMatch ? headingMatch[1] : null
          const body = heading ? section.replace(/^###\s.+\n/, '') : section

          return (
            <div key={i} style={{
              background: 'var(--panel-2)',
              borderRadius: 14,
              padding: '16px 18px',
              marginBottom: 12,
              border: '1px solid rgba(255,255,255,0.05)',
            }}>
              {heading && (
                <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10, color: 'var(--accent)' }}>
                  {heading}
                </div>
              )}
              <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text)', whiteSpace: 'pre-wrap' }}>
                {body.trim()}
              </div>
            </div>
          )
        })
      ) : (
        <div style={{
          background: 'var(--panel-2)',
          borderRadius: 14,
          padding: '18px',
          fontSize: 14,
          lineHeight: 1.8,
          whiteSpace: 'pre-wrap',
          border: '1px solid rgba(255,255,255,0.05)',
        }}>
          {summary}
        </div>
      )}
    </div>
  )
}

export default function Summary() {
  const [topic, setTopic]         = useState('oil')
  const [news, setNews]           = useState([])
  const [reddit, setReddit]       = useState([])
  const [summary, setSummary]     = useState(null)
  const [fetching, setFetching]   = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [fetchError, setFetchError]     = useState(null)
  const [analyzeError, setAnalyzeError] = useState(null)
  const [activeTab, setActiveTab] = useState('news')

  const fetchData = useCallback(async () => {
    setFetching(true)
    setFetchError(null)
    setSummary(null)
    setNews([])
    setReddit([])

    try {
      const [newsRes, redditRes] = await Promise.all([
        fetch(`${API}/api/news?topic=${topic}&limit=20`),
        fetch(`${API}/api/reddit?topic=${topic}&limit=20`),
      ])

      if (!newsRes.ok) {
        const err = await newsRes.json()
        throw new Error(err.detail || 'News fetch failed')
      }
      if (!redditRes.ok) {
        const err = await redditRes.json()
        throw new Error(err.detail || 'Reddit fetch failed')
      }

      const [newsData, redditData] = await Promise.all([newsRes.json(), redditRes.json()])
      setNews(newsData)
      setReddit(redditData)
      setActiveTab('news')
    } catch (e) {
      setFetchError(e.message)
    } finally {
      setFetching(false)
    }
  }, [topic])

  const generateSummary = useCallback(async () => {
    if (!news.length && !reddit.length) return
    setAnalyzing(true)
    setAnalyzeError(null)
    setSummary(null)

    try {
      const res = await fetch(`${API}/api/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, news, reddit }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis failed')
      }

      const data = await res.json()
      setSummary(data)
      setActiveTab('summary')
    } catch (e) {
      setAnalyzeError(e.message)
    } finally {
      setAnalyzing(false)
    }
  }, [topic, news, reddit])

  const hasData = news.length > 0 || reddit.length > 0

  return (
    <div>
      {/* Topic Selector */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>AI Summary Report</div>
            <div style={{ fontSize: 13, color: 'var(--muted)' }}>
              Fetch live news & Reddit data, then generate an OpenAI-powered market analysis
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {TOPICS.map(t => (
              <button
                key={t.id}
                onClick={() => { setTopic(t.id); setNews([]); setReddit([]); setSummary(null) }}
                style={{
                  padding: '8px 16px',
                  borderRadius: 12,
                  border: topic === t.id ? '2px solid var(--accent)' : '1px solid rgba(255,255,255,0.12)',
                  background: topic === t.id ? 'rgba(255,183,3,0.14)' : 'transparent',
                  color: topic === t.id ? 'var(--accent)' : 'var(--muted)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: 13,
                  transition: 'all 0.15s',
                }}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <button
          className="button"
          onClick={fetchData}
          disabled={fetching}
          style={{ opacity: fetching ? 0.6 : 1 }}
        >
          {fetching ? (
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Spinner /> Fetching Data…
            </span>
          ) : '⬇ Fetch News & Reddit'}
        </button>

        {hasData && (
          <button
            className="button"
            onClick={generateSummary}
            disabled={analyzing}
            style={{
              background: analyzing ? 'var(--accent-2)' : 'linear-gradient(135deg, #7b2ff7, #00f5d4)',
              opacity: analyzing ? 0.7 : 1,
            }}
          >
            {analyzing ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Spinner color="#fff" /> Analyzing with AI…
              </span>
            ) : '✨ Generate AI Summary'}
          </button>
        )}

        {hasData && (
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>
            {news.length} news · {reddit.length} reddit posts fetched
          </span>
        )}
      </div>

      {/* Error banners */}
      {fetchError   && <ErrorBanner msg={fetchError} />}
      {analyzeError && <ErrorBanner msg={analyzeError} />}

      {/* Content tabs */}
      {hasData && (
        <div className="card">
          <div style={{ display: 'flex', gap: 6, marginBottom: 18, borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 12 }}>
            {[
              { id: 'news',    label: `📰 News (${news.length})` },
              { id: 'reddit',  label: `💬 Reddit (${reddit.length})` },
              summary ? { id: 'summary', label: '✨ AI Summary' } : null,
            ].filter(Boolean).map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 10,
                  border: activeTab === tab.id ? '1px solid var(--accent)' : '1px solid transparent',
                  background: activeTab === tab.id ? 'rgba(255,183,3,0.12)' : 'transparent',
                  color: activeTab === tab.id ? 'var(--accent)' : 'var(--muted)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: 13,
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'news' && (
            <div style={{ maxHeight: 480, overflowY: 'auto', paddingRight: 4 }}>
              {news.length === 0
                ? <EmptyState msg="No news articles found." />
                : news.map((item, i) => <NewsCard key={i} item={item} />)
              }
            </div>
          )}

          {activeTab === 'reddit' && (
            <div style={{ maxHeight: 480, overflowY: 'auto', paddingRight: 4 }}>
              {reddit.length === 0
                ? <EmptyState msg="No Reddit posts found." />
                : reddit.map((item, i) => <RedditCard key={i} item={item} />)
              }
            </div>
          )}

          {activeTab === 'summary' && summary && (
            <AISummaryDisplay
              summary={summary.summary}
              model={summary.model}
              newsCount={summary.news_count}
              redditCount={summary.reddit_count}
            />
          )}
        </div>
      )}

      {/* Empty state */}
      {!hasData && !fetching && !fetchError && (
        <div className="card" style={{
          textAlign: 'center',
          padding: '48px 24px',
          border: '1px dashed rgba(255,255,255,0.12)',
          background: 'transparent',
        }}>
          <div style={{ fontSize: 40, marginBottom: 14 }}>🤖</div>
          <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 8 }}>No data yet</div>
          <div style={{ color: 'var(--muted)', fontSize: 14 }}>
            Select a topic above and click <strong style={{ color: 'var(--text)' }}>Fetch News & Reddit</strong> to get started.
            <br />Then generate an AI-powered market analysis using OpenAI.
          </div>
        </div>
      )}

      {/* Loading state */}
      {fetching && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <Spinner size={28} />
          <div style={{ marginTop: 14, color: 'var(--muted)', fontSize: 14 }}>
            Fetching live news & Reddit data for <strong style={{ color: 'var(--text)' }}>{topic}</strong>…
            <br /><span style={{ fontSize: 12 }}>Reddit may take 15–30s due to rate limiting</span>
          </div>
        </div>
      )}
    </div>
  )
}

function Spinner({ size = 16, color = 'currentColor' }) {
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      style={{ animation: 'spin 0.8s linear infinite', display: 'inline-block' }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  )
}

function ErrorBanner({ msg }) {
  return (
    <div style={{
      background: 'rgba(255,107,107,0.12)',
      border: '1px solid rgba(255,107,107,0.3)',
      borderRadius: 12,
      padding: '12px 16px',
      marginBottom: 16,
      fontSize: 13,
      color: 'var(--danger)',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    }}>
      ⚠ {msg}
    </div>
  )
}

function EmptyState({ msg }) {
  return (
    <div style={{ textAlign: 'center', padding: '32px', color: 'var(--muted)', fontSize: 14 }}>
      {msg}
    </div>
  )
}
