import { useState } from 'react'
import { api } from '../api.js'

export default function Backtest() {
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState('')

  async function runBacktest() {
    setStatus('Running...')
    try {
      const res = await api.backtest({
        strike_val: 100,
        direction: 'up',
        rsi_low: 45,
        rsi_high: 55,
        trade_on: 'futures',
        resample_rule: '1h'
      })
      setResult(res)
      setStatus('Done')
    } catch (err) {
      setStatus(`Error: ${err.message}`)
    }
  }

  const metrics = result?.metrics || {}

  return (
    <div className="grid">
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h3>Run Backtest</h3>
        <button className="button" onClick={runBacktest}>Run</button>
        <span style={{ marginLeft: 12, color: 'var(--muted)' }}>{status}</span>
      </div>
      {['total_return_pct','sharpe_ratio','max_drawdown_pct','buy_hold_return_pct','n_trades'].map((key) => (
        <div className="card" key={key}>
          <h3>{key.replace(/_/g,' ')}</h3>
          <div style={{ fontSize: 28, fontWeight: 600 }}>{metrics[key] ?? '—'}</div>
        </div>
      ))}
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <h3>Recent Trades</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>PnL</th>
            </tr>
          </thead>
          <tbody>
            {(result?.trades || []).slice(-10).reverse().map((t) => (
              <tr key={t.entry_date}>
                <td>{t.entry_date}</td>
                <td>{t.entry_price}</td>
                <td>{t.exit_price ?? '—'}</td>
                <td>{t.pnl ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
