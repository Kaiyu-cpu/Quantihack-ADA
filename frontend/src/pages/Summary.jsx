export default function Summary() {
  return (
    <div className="grid">
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h3>AI Summary Report</h3>
        <p>
          Polymarket prices showed early movement ahead of news spikes, while Reddit volume
          clustered around sharp price reversals. The RSI mean-reversion signal outperformed
          buy-and-hold when applied to futures prices, suggesting prediction-market timing
          helps improve entry/exit.
        </p>
        <div className="panel-row" style={{ marginTop: 12 }}>
          <span className="badge">Best Strike: $100 Up</span>
          <span className="badge">Sharpe: 0.42</span>
          <span className="badge">Lead/Lag: +6h</span>
        </div>
      </div>
    </div>
  )
}
