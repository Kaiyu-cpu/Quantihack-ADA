const sources = [
  {
    name: 'Polymarket Prices',
    description: 'Fetch YES-token prices for an event slug and persist CSV.',
    command: 'python ingestion/polymarket_fetcher.py'
  },
  {
    name: 'News Headlines',
    description: 'Pull recent headlines via Yahoo Finance tickers.',
    command: 'python ingestion/news_fetcher.py'
  },
  {
    name: 'Reddit Posts',
    description: 'Collect subreddit posts via Reddit public JSON API.',
    command: 'python ingestion/reddit_fetcher.py'
  },
  {
    name: 'GitHub Issues',
    description: 'Fetch issue history for repo health / survival analysis.',
    command: 'python ingestion/github_fetcher.py'
  }
]

export default function FetchData() {
  return (
    <div className="grid">
      {sources.map((source) => (
        <div className="card" key={source.name}>
          <h3>{source.name}</h3>
          <p>{source.description}</p>
          <div className="badge">Local Script</div>
          <div style={{ marginTop: 12 }}>
            <div style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, opacity: 0.8 }}>
              {source.command}
            </div>
            <button className="button" style={{ marginTop: 12 }}>
              Mark as Fetched
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
