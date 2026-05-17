/**
 * App.jsx
 * Root application component.
 * Handles routing with animated page transitions using AnimatePresence.
 * Mounts the global ToastProvider for notifications.
 */
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import Navbar        from './components/layout/Navbar'
import ToastProvider from './components/ui/ToastProvider'
import Dashboard     from './pages/Dashboard'
import Analyze       from './pages/Analyze'
import History       from './pages/History'
import './styles/globals.css'

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/"        element={<Dashboard />} />
        <Route path="/analyze" element={<Analyze />}   />
        <Route path="/history" element={<History />}   />
      </Routes>
    </AnimatePresence>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="scanlines">
        <Navbar />
        <AnimatedRoutes />
        <ToastProvider />
      </div>
    </BrowserRouter>
  )
}
