import { useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend)
import { api } from '../api.js'
import { useApp } from '../store.jsx'

export default function Backtest() {
  const { signalConfig } = useApp()
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState('')

  async function runBacktest() {
    setStatus('Running...')
    try {
      const res = await api.backtest({
        strike_val: signalConfig.strike,
        direction: signalConfig.direction,
        rsi_low: signalConfig.rsiLow,
        rsi_high: signalConfig.rsiHigh,
        trade_on: signalConfig.tradeOn,
        resample_rule: signalConfig.resample
      })
      setResult(res)
      setStatus('Done')
    } catch (err) {
      setStatus(`Error: ${err.message}`)
    }
  }

  const metrics = result?.metrics || {}

  const equity = result?.equity_curve || []
  const chartData = {
    labels: equity.map((p) => p.date),
    datasets: [
      {
        label: 'Equity',
        data: equity.map((p) => p.value),
        borderColor: '#ffb703',
        backgroundColor: 'rgba(255, 183, 3, 0.2)',
        tension: 0.3
      }
    ]
  }

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
        <h3>Equity Curve</h3>
        {equity.length ? <Line data={chartData} /> : <p>No results yet.</p>}
      </div>
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
