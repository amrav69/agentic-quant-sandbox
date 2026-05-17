/**
 * PageWrapper.jsx
 * Wraps every page with animated entry/exit transitions.
 * Use AnimatePresence in App.jsx to enable exit animations between routes.
 */
import { motion } from 'framer-motion'
import { pageTransition } from '../animations/motionVariants'

export default function PageWrapper({ children }) {
  return (
    <motion.main
      variants={pageTransition}
      initial="hidden"
      animate="visible"
      exit="exit"
      className="flex-1 pt-16 min-h-screen"
      style={{ background: 'var(--bg-primary)' }}
    >
      {children}
    </motion.main>
  )
}
