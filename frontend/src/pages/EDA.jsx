export default function EDA() {
  return (
    <div className="grid">
      <div className="card">
        <h3>Dataset Overview</h3>
        <p>Confirm ranges, strike counts, and data freshness before modeling.</p>
        <ul>
          <li>Polymarket rows: 11,347</li>
          <li>Strikes: 21</li>
          <li>Date range: 2026-02-28 → 2026-03-28</li>
        </ul>
      </div>
      <div className="card">
        <h3>Liquidity Snapshot</h3>
        <p>Pick the most liquid strike to avoid noisy signals.</p>
        <div className="panel-row">
          <span className="badge">Strike $100</span>
          <span className="badge">Direction: Up</span>
        </div>
      </div>
      <div className="card">
        <h3>News & Reddit Activity</h3>
        <p>Use volume spikes to spot narrative shifts.</p>
        <div className="panel-row">
          <span className="badge">News: 37</span>
          <span className="badge">Reddit: 221</span>
        </div>
      </div>
    </div>
  )
}
