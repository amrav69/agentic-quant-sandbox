/**
 * CodeGenPanel.jsx
 * Step 2 agent card — shows generated Python backtest code via CodeBlock.
 */
import { motion } from 'framer-motion'
import { Code2 } from 'lucide-react'
import CodeBlock from '../ui/CodeBlock'
import { fadeUp } from '../animations/motionVariants'

/** Strip markdown code fences from LLM output */
function stripFences(code = '') {
  return code.replace(/^```[\w]*\n?/, '').replace(/\n?```$/, '').trim()
}

export default function CodeGenPanel({ code = '' }) {
  const clean = stripFences(code)

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      className="rounded-2xl overflow-hidden"
      style={{ border: '2px solid rgba(124,58,237,0.4)', background: 'rgba(124,58,237,0.03)', boxShadow: '0 0 40px rgba(124,58,237,0.1)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'rgba(124,58,237,0.2)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(124,58,237,0.15)' }}>
            <Code2 size={16} style={{ color: '#7c3aed' }} />
          </div>
          <div>
            <p className="font-semibold text-sm">CodeGen Agent</p>
            <p className="text-[10px] uppercase tracking-widest" style={{ color: '#7c3aed' }}>Step 2 · Backtest Generated</p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-3 py-1 rounded-full" style={{ color: '#7c3aed', background: 'rgba(124,58,237,0.15)' }}>
          DONE
        </span>
      </div>

      {/* Code block */}
      <div className="p-4">
        <CodeBlock code={clean} language="python" title="vectorbt_backtest.py" maxHeight="380px" />
      </div>
    </motion.div>
  )
}
