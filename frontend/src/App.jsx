import { NavLink, Routes, Route } from 'react-router-dom'
import FetchData from './pages/FetchData.jsx'
import EDA from './pages/EDA.jsx'
import SignalGenerator from './pages/SignalGenerator.jsx'
import Backtest from './pages/Backtest.jsx'
import Summary from './pages/Summary.jsx'

const navItems = [
  { to: '/', label: 'Fetch Data' },
  { to: '/eda', label: 'EDA' },
  { to: '/signals', label: 'Signal Generator' },
  { to: '/backtest', label: 'Backtest' },
  { to: '/report', label: 'AI Summary' }
]

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">QuantiHack ADA</div>
        <nav>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              end={item.to === '/'}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <header className="header">
          <h1>Alternative Data Alpha</h1>
          <span>Polymarket • News • Reddit • GitHub</span>
        </header>
        <Routes>
          <Route path="/" element={<FetchData />} />
          <Route path="/eda" element={<EDA />} />
          <Route path="/signals" element={<SignalGenerator />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/report" element={<Summary />} />
        </Routes>
      </main>
    </div>
  )
}
