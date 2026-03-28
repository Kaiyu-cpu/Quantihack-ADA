export default function SignalGenerator() {
  return (
    <div className="grid">
      <div className="card">
        <h3>Manual Signal Recipe</h3>
        <p>Configure RSI thresholds and indicator windows.</p>
        <div className="panel-row">
          <input className="input" placeholder="RSI Low (e.g. 45)" />
          <input className="input" placeholder="RSI High (e.g. 55)" />
        </div>
        <div className="panel-row" style={{ marginTop: 12 }}>
          <input className="input" placeholder="RSI Window (14)" />
          <input className="input" placeholder="BB Window (20)" />
        </div>
        <button className="button" style={{ marginTop: 16 }}>Generate Signals</button>
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
