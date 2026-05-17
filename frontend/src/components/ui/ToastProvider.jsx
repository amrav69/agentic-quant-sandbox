/**
 * ToastProvider.jsx
 * Global toast notification system.
 *
 * Usage:
 *   1. Wrap your app with <ToastProvider />
 *   2. Call addNotification({ type, message }) from Zustand store anywhere
 *
 * Variants: 'success' | 'error' | 'info' | 'warning'
 */
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react'
import useStore from '../../store/useStore'

/* ── Toast appearance config ── */
const TOAST_CONFIG = {
  success: { icon: CheckCircle,    color: '#10b981', bg: '#10b98118' },
  error:   { icon: XCircle,        color: '#ef4444', bg: '#ef444418' },
  info:    { icon: Info,           color: '#00f5ff', bg: '#00f5ff12' },
  warning: { icon: AlertTriangle,  color: '#f59e0b', bg: '#f59e0b18' },
}

/* ── Single Toast Item ── */
function Toast({ id, type = 'info', message }) {
  const dismissNotification = useStore((s) => s.dismissNotification)
  const { icon: Icon, color, bg } = TOAST_CONFIG[type] ?? TOAST_CONFIG.info

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 60, scale: 0.9  }}
      animate={{ opacity: 1, x: 0,  scale: 1    }}
      exit={{    opacity: 0, x: 60, scale: 0.92 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      className="glass rounded-xl px-4 py-3 flex items-start gap-3 min-w-[280px] max-w-[360px] shadow-xl"
      style={{ border: `1px solid ${color}30` }}
    >
      {/* Icon */}
      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
        style={{ background: bg }}>
        <Icon size={15} style={{ color }} />
      </div>

      {/* Message */}
      <p className="flex-1 text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
        {message}
      </p>

      {/* Dismiss */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => dismissNotification(id)}
        className="shrink-0 mt-0.5 rounded-md p-0.5 transition-colors"
        style={{ color: 'var(--text-muted)' }}
      >
        <X size={13} />
      </motion.button>
    </motion.div>
  )
}

/* ── Provider ── */
export default function ToastProvider() {
  const notifications = useStore((s) => s.notifications)

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 items-end pointer-events-none">
      <AnimatePresence mode="popLayout">
        {notifications.map((n) => (
          <div key={n.id} className="pointer-events-auto">
            <Toast {...n} />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}
