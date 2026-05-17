/**
 * useStore.js
 * Root Zustand store — four slices + history slice.
 */
import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

/* ─── Seed data so History page isn't empty on first visit ─── */
const SEED_HISTORY = [
  {
    id: 1,
    symbol: 'BTC-USD',
    timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    verdict: 'FAIL',
    sharpe: 0.82,
    regime: 'Ranging',
    research:  { analysis: 'BTC-USD is in a ranging market. RSI at 48 near neutral. MACD line is below signal — bearish short-term momentum. EMA20 crossing below EMA50 suggests further downside risk. Recommend waiting for a clear directional break before entering.' },
    code:      { code: 'import vectorbt as vbt\nimport yfinance as yf\n\ndata = yf.download("BTC-USD", period="1y")\nclose = data["Close"]\nrsi = vbt.ta.rsi(close, length=14)\nentries = rsi < 30\nexits = rsi > 70\npf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000)\nprint(pf.sharpe_ratio(), pf.max_drawdown())' },
    critique:  { verdict: 'FAIL', issues: ['No transaction costs modelled', 'Lookahead bias risk in RSI entry condition', 'Backtest period too short for statistical significance'], suggestions: ['Add 0.1% per-trade commission', 'Use shifted RSI signal to avoid lookahead', 'Extend backtest to 3+ years'] },
    indicators: { RSI: 48.22, EMA20: 78432.02, EMA50: 78374.74, ATR: 27.63, MACD: -35.9, current_price: 78413.5 },
  },
  {
    id: 2,
    symbol: 'AAPL',
    timestamp: new Date(Date.now() - 11 * 60 * 1000).toISOString(),
    verdict: 'PASS',
    sharpe: 1.74,
    regime: 'Bullish',
    research:  { analysis: 'AAPL is showing strong bullish momentum. RSI at 59 with room to run. EMA20 above EMA50 confirms trend. MACD line crossing above signal — buy signal confirmed. Price holding above key support at $298. Moderate volume confirms institutional participation.' },
    code:      { code: 'import vectorbt as vbt\nimport yfinance as yf\n\ndata = yf.download("AAPL", period="2y")\nclose = data["Close"]\nema20 = close.ewm(span=20).mean()\nema50 = close.ewm(span=50).mean()\nentries = ema20 > ema50\nexits = ema20 < ema50\npf = vbt.Portfolio.from_signals(close, entries, exits, sl_stop=0.05)\nprint(f"Sharpe: {pf.sharpe_ratio():.2f} | DD: {pf.max_drawdown():.1%}")' },
    critique:  { verdict: 'PASS', issues: ['Stop loss set too tight at 5%', 'No position sizing applied'], suggestions: ['Consider 8-10% stop based on ATR', 'Apply Kelly criterion for position sizing'] },
    indicators: { RSI: 59.21, EMA20: 299.1, EMA50: 294.65, ATR: 1.86, MACD: 2.44, current_price: 300.22 },
  },
  {
    id: 3,
    symbol: 'ETH-USD',
    timestamp: new Date(Date.now() - 28 * 60 * 1000).toISOString(),
    verdict: 'FAIL',
    sharpe: -0.21,
    regime: 'Bearish',
    research:  { analysis: 'ETH-USD is in a clear bearish structure. RSI at 38, approaching oversold but no reversal signal yet. EMA20 below EMA50 with widening spread. MACD deeply negative. Volume declining — lack of buyer conviction. High short-term risk.' },
    code:      { code: 'import vectorbt as vbt\nimport yfinance as yf\n\ndata = yf.download("ETH-USD", period="1y")\nclose = data["Close"]\nrsi = vbt.ta.rsi(close, length=14)\nmacd = vbt.ta.macd(close)\nentries = (rsi < 35) & (macd.macd > macd.signal)\nexits = rsi > 65\npf = vbt.Portfolio.from_signals(close, entries, exits)\nprint(pf.stats())' },
    critique:  { verdict: 'FAIL', issues: ['Negative Sharpe ratio makes strategy unprofitable', 'No slippage model', 'Entry conditions too aggressive during downtrend'], suggestions: ['Add trend filter — only enter longs in bullish regime', 'Model 0.2% slippage per trade', 'Consider mean-reversion strategy instead of trend-following in ranging/bearish markets'] },
    indicators: { RSI: 38.32, EMA20: 3489.5, EMA50: 3612.8, ATR: 45.2, MACD: -42.1, current_price: 3521.88 },
  },
  {
    id: 4,
    symbol: 'NVDA',
    timestamp: new Date(Date.now() - 47 * 60 * 1000).toISOString(),
    verdict: 'PASS',
    sharpe: 2.31,
    regime: 'Bullish',
    research:  { analysis: 'NVDA in strong momentum-driven uptrend. RSI at 67 — bullish but not overbought. EMA crossover confirmed 2 weeks ago. Earnings catalyst ahead. Sector rotation into AI/chip stocks supports upside. Recommended: long entry on any 2-3% pullback with ATR-based stop.' },
    code:      { code: 'import vectorbt as vbt\nimport yfinance as yf\n\ndata = yf.download("NVDA", period="2y")\nclose = data["Close"]\natr = vbt.ta.atr(data["High"], data["Low"], close, length=14)\nrsi = vbt.ta.rsi(close, length=14)\nentries = rsi < 50\nexits = (rsi > 70) | (close < close.shift(1) - 2 * atr)\npf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, sl_stop=2 * atr)\nprint(f"Sharpe: {pf.sharpe_ratio():.2f}")' },
    critique:  { verdict: 'PASS', issues: ['ATR-based stop may be too wide for short-term trades'], suggestions: ['Reduce ATR multiplier from 2x to 1.5x for tighter risk control', 'Add volume confirmation for entry signals'] },
    indicators: { RSI: 67.1, EMA20: 858.4, EMA50: 831.2, ATR: 12.8, MACD: 15.2, current_price: 875.6 },
  },
]

/* ─── Analysis Slice ─── */
const createAnalysisSlice = (set) => ({
  symbol:            '',
  setSymbol:         (symbol) => set({ symbol }),
  researchResult:    null,
  setResearchResult: (data) => set({ researchResult: data }),
  generatedCode:     null,
  setGeneratedCode:  (data) => set({ generatedCode: data }),
  critiqueResult:    null,
  setCritiqueResult: (data) => set({ critiqueResult: data }),
  liveIndicators:    null,
  setLiveIndicators: (data) => set({ liveIndicators: data }),
  clearAnalysis: () => set({ researchResult: null, generatedCode: null, critiqueResult: null, liveIndicators: null }),
})

/* ─── UI Slice ─── */
const createUISlice = (set) => ({
  isLoading:     false,
  setIsLoading:  (val) => set({ isLoading: val }),
  activeStep:    null,
  setActiveStep: (step) => set({ activeStep: step }),
  sidebarOpen:   true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  activeModal:   null,
  openModal:     (id) => set({ activeModal: id }),
  closeModal:    () => set({ activeModal: null }),
})

/* ─── Ticker Slice ─── */
const createTickerSlice = (set, get) => ({
  activeTicker:    'BTC-USD',
  setActiveTicker: (ticker) => set({ activeTicker: ticker.toUpperCase() }),
  recentTickers:   ['BTC-USD', 'ETH-USD', 'AAPL'],
  addRecentTicker: (ticker) => {
    const clean = ticker.toUpperCase()
    const current = get().recentTickers.filter((t) => t !== clean)
    set({ recentTickers: [clean, ...current].slice(0, 10) })
  },
})

/* ─── Notifications Slice ─── */
const createNotificationSlice = (set, get) => ({
  notifications: [],
  addNotification: ({ type = 'info', message }) => {
    const id = Date.now()
    set((s) => ({ notifications: [...s.notifications, { id, type, message }] }))
    setTimeout(() => {
      set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) }))
    }, 4000)
  },
  dismissNotification: (id) =>
    set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),
})

/* ─── History Slice ─── */
const createHistorySlice = (set, get) => ({
  analysisHistory: SEED_HISTORY,

  addHistoryEntry: (entry) => {
    const newEntry = { id: Date.now(), timestamp: new Date().toISOString(), ...entry }
    set((s) => ({ analysisHistory: [newEntry, ...s.analysisHistory].slice(0, 50) }))
  },

  clearHistory: () => set({ analysisHistory: [] }),
})

/* ─── Root Store ─── */
const useStore = create(
  devtools(
    (set, get) => ({
      ...createAnalysisSlice(set, get),
      ...createUISlice(set, get),
      ...createTickerSlice(set, get),
      ...createNotificationSlice(set, get),
      ...createHistorySlice(set, get),
    }),
    { name: 'AgenticQuantStore' }
  )
)

export default useStore
