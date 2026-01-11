import { useState } from 'react'
import { motion } from 'framer-motion'
import { Activity, TrendingUp, Zap, RefreshCw } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { refreshData } from '../lib/api'
import type { TabType } from '../App'

interface HeaderProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
}

export function Header({ activeTab, onTabChange }: HeaderProps) {
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const refreshMutation = useMutation({
    mutationFn: refreshData,
    onSuccess: (data) => {
      setRefreshMessage(`Refreshed ${data.games_in_list} games`)
      // Invalidate queries to refetch data
      queryClient.invalidateQueries({ queryKey: ['trending'] })
      queryClient.invalidateQueries({ queryKey: ['trend-stats'] })
      queryClient.invalidateQueries({ queryKey: ['genres'] })
      setTimeout(() => setRefreshMessage(null), 3000)
    },
    onError: () => {
      setRefreshMessage('Refresh failed')
      setTimeout(() => setRefreshMessage(null), 3000)
    }
  })

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
            className="hidden md:flex items-center gap-2"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <NavLink
              icon={<TrendingUp className="w-4 h-4" />}
              label="Trends"
              active={activeTab === 'trends'}
              onClick={() => onTabChange('trends')}
            />
            <NavLink
              icon={<Activity className="w-4 h-4" />}
              label="Analytics"
              active={activeTab === 'analytics'}
              onClick={() => onTabChange('analytics')}
            />
          </motion.nav>

          {/* Status & Refresh */}
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            {refreshMessage && (
              <span className="text-xs text-aurora-green font-medium">
                {refreshMessage}
              </span>
            )}
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-aurora-deep-blue/70 hover:text-aurora-deep-blue bg-aurora-cyan/10 hover:bg-aurora-cyan/20 rounded-lg transition-all duration-200 disabled:opacity-50"
              title="Refresh game data from Roblox API"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
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
  onClick,
}: {
  icon: React.ReactNode
  label: string
  active?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
        active
          ? 'bg-aurora-gradient text-aurora-deep-blue font-medium shadow-sm'
          : 'text-aurora-deep-blue/60 hover:text-aurora-deep-blue hover:bg-aurora-cyan/10'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
