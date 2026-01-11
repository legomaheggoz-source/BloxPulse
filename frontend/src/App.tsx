import { motion } from 'framer-motion'
import { Header } from './components/Header'
import { Dashboard } from './components/Dashboard'
import { StatsBar } from './components/StatsBar'

function App() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Stats Overview */}
          <StatsBar />

          {/* Dashboard */}
          <Dashboard />
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-aurora-cyan/20 py-6 mt-12">
        <div className="container mx-auto px-4 text-center text-sm text-aurora-deep-blue/60">
          <p>BloxPulse - Roblox Market Intelligence Engine</p>
          <p className="mt-1">Data refreshes every 6 hours</p>
        </div>
      </footer>
    </div>
  )
}

export default App
