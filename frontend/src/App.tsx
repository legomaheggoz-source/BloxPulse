import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Header } from './components/Header'
import { Dashboard } from './components/Dashboard'
import { Analytics } from './components/Analytics'
import { StatsBar } from './components/StatsBar'

export type TabType = 'trends' | 'analytics'

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('trends')

  return (
    <div className="min-h-screen">
      {/* Header */}
      <Header activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Stats Overview */}
          <StatsBar />

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            {activeTab === 'trends' ? (
              <motion.div
                key="trends"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.2 }}
              >
                <Dashboard />
              </motion.div>
            ) : (
              <motion.div
                key="analytics"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
              >
                <Analytics />
              </motion.div>
            )}
          </AnimatePresence>
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
