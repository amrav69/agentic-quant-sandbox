/**
 * apiClient.js
 * Centralized Axios API client for all backend communication.
 * Backend base URL: http://127.0.0.1:8000
 */
import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 60000, // 60s timeout - LLM calls can be slow
  headers: {
    'Content-Type': 'application/json',
    'Accept':       'application/json',
  },
})

/* ─── Request Interceptor ───────────────────────────────────────────────────
   Runs before every outgoing request.
   Good place to inject auth tokens or log requests in dev mode.
─────────────────────────────────────────────────────────────────────────────*/
apiClient.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data ?? '')
    }
    return config
  },
  (error) => Promise.reject(error)
)

/* ─── Response Interceptor ──────────────────────────────────────────────────
   Runs on every incoming response.
   Standardizes error handling so callers don't need to inspect axios internals.
─────────────────────────────────────────────────────────────────────────────*/
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail ?? error?.message ?? 'Unknown error'
    console.error(`[API Error] ${detail}`)
    return Promise.reject(new Error(detail))
  }
)

/* ─── API Methods ───────────────────────────────────────────────────────────*/

/** GET /health – Check backend is alive */
export const checkHealth = () => apiClient.get('/health')

/**
 * GET /analyze/{symbol} – Fully autonomous analysis.
 * Fetches live data, calculates indicators, and returns AI analysis.
 */
export const analyzeSymbol = (symbol) => apiClient.get(`/analyze/${symbol}`)

/**
 * POST /analyze – Manual analysis with a raw market data dict.
 * @param {Object} data - { symbol, price, rsi, macd, volume_trend }
 */
export const analyzeManual = (data) => apiClient.post('/analyze', data)

/**
 * POST /generate – Runs Research + CodeGen pipeline.
 * @param {Object} data - { symbol, price, rsi, macd, volume_trend }
 */
export const generateBacktest = (data) => apiClient.post('/generate', data)

/**
 * POST /critique – Runs full Research → CodeGen → Critic pipeline.
 * @param {Object} data - { symbol, price, rsi, macd, volume_trend }
 */
export const critiqueStrategy = (data) => apiClient.post('/critique', data)

export default apiClient
