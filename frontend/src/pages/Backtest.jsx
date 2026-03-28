const metrics = [
  { label: 'Total Return', value: '-0.38%' },
  { label: 'Sharpe Ratio', value: '-0.29' },
  { label: 'Max Drawdown', value: '-0.65%' },
  { label: 'Trades', value: '24' }
]

export default function Backtest() {
  return (
    <div className="grid">
      {metrics.map((metric) => (
        <div className="card" key={metric.label}>
          <h3>{metric.label}</h3>
          <div style={{ fontSize: 28, fontWeight: 600 }}>{metric.value}</div>
        </div>
      ))}
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h3>Equity Curve</h3>
        <p>Wire this to the backtest results API.</p>
        <div style={{ height: 200, background: 'rgba(255,255,255,0.04)', borderRadius: 12 }} />
      </div>
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h3>Recent Trades</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Signal</th>
              <th>Price</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>2026-03-26 12:00</td>
              <td>Buy</td>
              <td>0.58</td>
              <td>+0.6%</td>
            </tr>
            <tr>
              <td>2026-03-27 09:00</td>
              <td>Sell</td>
              <td>0.61</td>
              <td>-0.4%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
