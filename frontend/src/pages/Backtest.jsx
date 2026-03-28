import { useState } from 'react'
import { Line, Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  LineElement,
  BarElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(LineElement, BarElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend)
import { api } from '../api.js'
import { useApp } from '../store.jsx'

export default function Backtest() {
  const { signalConfig, setSignalConfig } = useApp()
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
        resample_rule: signalConfig.resample,
        lead_hours: signalConfig.leadHours,
        signal_type: signalConfig.signalType
      })
      setResult(res)
      setStatus('Done')
    } catch (err) {
      setStatus(`Error: ${err.message}`)
    }
  }

  const metrics = result?.metrics || {}
  const equity = result?.equity_curve || []
  const trades = result?.trades || []
  const signalCounts = result?.signal_counts || { buy: 0, sell: 0, hold: 0 }
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
        <h3>Backtest Parameters</h3>
        <div className="panel-row">
          <label>
            Strike
            <input
              className="input"
              value={signalConfig.strike}
              onChange={(e) => setSignalConfig({ ...signalConfig, strike: Number(e.target.value) })}
            />
          </label>
          <label>
            Direction
            <select
              className="input"
              value={signalConfig.direction}
              onChange={(e) => setSignalConfig({ ...signalConfig, direction: e.target.value })}
            >
              <option value="up">up</option>
              <option value="down">down</option>
            </select>
          </label>
          <label>
            RSI Low
            <input
              className="input"
              value={signalConfig.rsiLow}
              onChange={(e) => setSignalConfig({ ...signalConfig, rsiLow: Number(e.target.value) })}
            />
          </label>
          <label>
            RSI High
            <input
              className="input"
              value={signalConfig.rsiHigh}
              onChange={(e) => setSignalConfig({ ...signalConfig, rsiHigh: Number(e.target.value) })}
            />
          </label>
          <label>
            Trade On
            <select
              className="input"
              value={signalConfig.tradeOn}
              onChange={(e) => setSignalConfig({ ...signalConfig, tradeOn: e.target.value })}
            >
              <option value="polymarket">polymarket</option>
              <option value="futures">futures</option>
            </select>
          </label>
          <label>
            Signal Type
            <select
              className="input"
              value={signalConfig.signalType}
              onChange={(e) => setSignalConfig({ ...signalConfig, signalType: e.target.value })}
            >
              <option value="rsi">RSI</option>
              <option value="true_price">True Price</option>
            </select>
          </label>
          <label>
            Lead Hours
            <input
              className="input"
              value={signalConfig.leadHours}
              onChange={(e) => setSignalConfig({ ...signalConfig, leadHours: Number(e.target.value) })}
            />
          </label>
          <label>
            Resample
            <select
              className="input"
              value={signalConfig.resample}
              onChange={(e) => setSignalConfig({ ...signalConfig, resample: e.target.value })}
            >
              <option value="1h">1h</option>
              <option value="30m">30m</option>
              <option value="15m">15m</option>
              <option value="1d">1d</option>
            </select>
          </label>
        </div>
      </div>
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
        <h3>Signal Distribution</h3>
        {equity.length ? (
          <Bar
            data={{
              labels: ['Buy', 'Sell', 'Hold'],
              datasets: [
                {
                  label: 'Signals',
                  data: [signalCounts.buy, signalCounts.sell, signalCounts.hold],
                  backgroundColor: 'rgba(0,245,212,0.6)'
                }
              ]
            }}
          />
        ) : (
          <p>No trades yet.</p>
        )}
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
