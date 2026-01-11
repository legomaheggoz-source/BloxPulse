import { motion } from 'framer-motion'
import { Activity, TrendingUp, Zap } from 'lucide-react'

export function Header() {
  return (
    <header className="glass-panel mx-4 mt-4 mb-6">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo & Title */}
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="relative">
              <div className="w-10 h-10 rounded-lg bg-aurora-gradient flex items-center justify-center">
                <Zap className="w-6 h-6 text-aurora-deep-blue" />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-aurora-green rounded-full border-2 border-white animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-aurora-deep-blue">
                Blox<span className="text-aurora-gradient">Pulse</span>
              </h1>
              <p className="text-xs text-aurora-deep-blue/60">
                Roblox Market Intelligence
              </p>
            </div>
          </motion.div>

          {/* Navigation */}
          <motion.nav
            className="hidden md:flex items-center gap-6"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <NavLink icon={<TrendingUp className="w-4 h-4" />} label="Trends" active />
            <NavLink icon={<Activity className="w-4 h-4" />} label="Analytics" />
          </motion.nav>

          {/* Status */}
          <motion.div
            className="flex items-center gap-2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="hidden sm:flex items-center gap-2 text-xs text-aurora-deep-blue/60">
              <span className="w-2 h-2 bg-aurora-green rounded-full animate-pulse" />
              <span>Live Data</span>
            </div>
          </motion.div>
        </div>
      </div>
    </header>
  )
}

function NavLink({
  icon,
  label,
  active = false,
}: {
  icon: React.ReactNode
  label: string
  active?: boolean
}) {
  return (
    <button
      className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 ${
        active
          ? 'bg-aurora-cyan/20 text-aurora-deep-blue font-medium'
          : 'text-aurora-deep-blue/60 hover:text-aurora-deep-blue hover:bg-aurora-cyan/10'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
