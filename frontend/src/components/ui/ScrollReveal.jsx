/**
 * ScrollReveal.jsx
 * Viewport-triggered fade-up animation wrapper.
 * Any children placed inside will animate in when they enter the viewport.
 *
 * Props:
 *  - children     : React children
 *  - delay (num)  : Stagger delay in seconds (default: 0)
 *  - y (num)      : Initial Y offset to slide up from (default: 28)
 *  - once (bool)  : Animate only once (default: true)
 *  - className    : Pass-through class names
 */
import { motion } from 'framer-motion'

export default function ScrollReveal({
  children,
  delay = 0,
  y = 28,
  once = true,
  className = '',
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y, filter: 'blur(4px)' }}
      whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      viewport={{ once, margin: '-60px' }}
      transition={{
        duration: 0.55,
        delay,
        ease: [0.16, 1, 0.3, 1], // expo-out
      }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
