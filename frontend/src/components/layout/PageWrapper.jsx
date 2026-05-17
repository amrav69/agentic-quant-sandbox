/**
 * PageWrapper.jsx
 * Animated page transition wrapper.
 * Offsets below the fixed navbar via padding-top = --navbar-h (64px).
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
      className="flex-1 min-h-screen"
      style={{ paddingTop: 'var(--navbar-h)', background: 'var(--bg-primary)' }}
    >
      {children}
    </motion.main>
  )
}
