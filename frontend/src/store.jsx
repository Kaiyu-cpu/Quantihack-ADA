import { createContext, useContext, useState } from 'react'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [signalConfig, setSignalConfig] = useState({
    strike: 100,
    direction: 'up',
    rsiLow: 45,
    rsiHigh: 55,
    resample: '1h',
    tradeOn: 'futures'
  })

  return (
    <AppContext.Provider value={{ signalConfig, setSignalConfig }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
