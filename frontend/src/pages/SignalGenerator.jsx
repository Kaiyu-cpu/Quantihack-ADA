import { useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'

export default function SignalGenerator() {
  const { signalConfig, setSignalConfig } = useApp()
  const [strike, setStrike] = useState(signalConfig.strike)
  const [direction, setDirection] = useState(signalConfig.direction)
  const [rsiLow, setRsiLow] = useState(signalConfig.rsiLow)
  const [rsiHigh, setRsiHigh] = useState(signalConfig.rsiHigh)
  const [status, setStatus] = useState('')
  const [suggestion, setSuggestion] = useState('')

  async function previewSignals() {
    setStatus('Running...')
    try {
      const result = await api.previewSignals({
        strike_val: Number(strike),
        direction,
        rsi_low: Number(rsiLow),
        rsi_high: Number(rsiHigh),
        resample_rule: '1h'
      })
      const counts = result.signal_counts || {}
      const buy = counts['1'] ?? counts[1] ?? 0
      const sell = counts['-1'] ?? counts[-1] ?? 0
      const hold = counts['0'] ?? counts[0] ?? 0
      setStatus(`Signals — Buy: ${buy} | Sell: ${sell} | Hold: ${hold}`)
      setSignalConfig({
        ...signalConfig,
        strike: Number(strike),
        direction,
        rsiLow: Number(rsiLow),
        rsiHigh: Number(rsiHigh)
      })
    } catch (err) {
      setStatus(`Error: ${err.message}`)
    }
  }

  async function suggestParams() {
    try {
      const res = await api.suggestSignals({ strike_val: Number(strike), direction })
      setSuggestion(`Suggested RSI: ${res.rsi_low}/${res.rsi_high} — ${res.note ?? ''}`)
      setRsiLow(res.rsi_low)
      setRsiHigh(res.rsi_high)
    } catch (err) {
      setSuggestion(`Error: ${err.message}`)
    }
  }

  return (
    <div className="grid">
      <div className="card">
        <h3>Manual Signal Recipe</h3>
        <p>Configure RSI thresholds and indicator windows.</p>
        <div className="panel-row">
          <label>
            Strike
            <input className="input" value={strike} onChange={(e) => setStrike(e.target.value)} placeholder="100" />
          </label>
          <label>
            Direction
            <input className="input" value={direction} onChange={(e) => setDirection(e.target.value)} placeholder="up" />
          </label>
        </div>
        <div className="panel-row" style={{ marginTop: 12 }}>
          <label>
            RSI Low
            <input className="input" value={rsiLow} onChange={(e) => setRsiLow(e.target.value)} placeholder="45" />
          </label>
          <label>
            RSI High
            <input className="input" value={rsiHigh} onChange={(e) => setRsiHigh(e.target.value)} placeholder="55" />
          </label>
        </div>
        <button className="button" style={{ marginTop: 16 }} onClick={previewSignals}>Generate Signals</button>
        <div style={{ marginTop: 10, color: 'var(--muted)' }}>{status}</div>
      </div>
      <div className="card">
        <h3>AI-Assisted Tuning</h3>
        <p>Use AI to recommend thresholds based on backtest performance.</p>
        <button className="button secondary" onClick={suggestParams}>Suggest Parameters</button>
        <div style={{ marginTop: 10, color: 'var(--muted)' }}>{suggestion}</div>
        <p style={{ marginTop: 12, color: 'var(--muted)' }}>
          Coming next: auto-select strike, direction, and thresholds.
        </p>
      </div>
    </div>
  )
}
