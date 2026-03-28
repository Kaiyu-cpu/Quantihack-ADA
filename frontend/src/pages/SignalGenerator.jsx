import { useState } from 'react'
import { api } from '../api.js'

export default function SignalGenerator() {
  const [strike, setStrike] = useState(100)
  const [direction, setDirection] = useState('up')
  const [rsiLow, setRsiLow] = useState(45)
  const [rsiHigh, setRsiHigh] = useState(55)
  const [status, setStatus] = useState('')

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
      setStatus(`Signals: ${JSON.stringify(result.signal_counts)}`)
    } catch (err) {
      setStatus(`Error: ${err.message}`)
    }
  }

  return (
    <div className="grid">
      <div className="card">
        <h3>Manual Signal Recipe</h3>
        <p>Configure RSI thresholds and indicator windows.</p>
        <div className="panel-row">
          <input className="input" value={strike} onChange={(e) => setStrike(e.target.value)} placeholder="Strike" />
          <input className="input" value={direction} onChange={(e) => setDirection(e.target.value)} placeholder="Direction" />
        </div>
        <div className="panel-row" style={{ marginTop: 12 }}>
          <input className="input" value={rsiLow} onChange={(e) => setRsiLow(e.target.value)} placeholder="RSI Low (45)" />
          <input className="input" value={rsiHigh} onChange={(e) => setRsiHigh(e.target.value)} placeholder="RSI High (55)" />
        </div>
        <button className="button" style={{ marginTop: 16 }} onClick={previewSignals}>Generate Signals</button>
        <div style={{ marginTop: 10, color: 'var(--muted)' }}>{status}</div>
      </div>
      <div className="card">
        <h3>AI-Assisted Tuning</h3>
        <p>Use AI to recommend thresholds based on backtest performance.</p>
        <button className="button secondary">Suggest Parameters</button>
        <p style={{ marginTop: 12, color: 'var(--muted)' }}>
          Coming next: auto-select strike, direction, and thresholds.
        </p>
      </div>
    </div>
  )
}
