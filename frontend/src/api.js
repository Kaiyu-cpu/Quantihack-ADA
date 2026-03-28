const BASE_URL = 'http://localhost:8000'

export async function fetchJson(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  health: () => fetchJson('/health'),
  fetchPolymarket: (body) => fetchJson('/fetch/polymarket', { method: 'POST', body: JSON.stringify(body) }),
  fetchNews: (body) => fetchJson('/fetch/news', { method: 'POST', body: JSON.stringify(body) }),
  fetchReddit: (body) => fetchJson('/fetch/reddit', { method: 'POST', body: JSON.stringify(body) }),
  fetchGithub: () => fetchJson('/fetch/github', { method: 'POST' }),
  edaPolymarket: () => fetchJson('/eda/polymarket'),
  previewSignals: (body) => fetchJson('/signals/preview', { method: 'POST', body: JSON.stringify(body) }),
  suggestSignals: (body) => fetchJson('/signals/suggest', { method: 'POST', body: JSON.stringify(body || {}) }),
  backtest: (body) => fetchJson('/backtest', { method: 'POST', body: JSON.stringify(body) }),
  summary: () => fetchJson('/summary')
}
