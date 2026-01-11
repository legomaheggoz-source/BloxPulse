import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Users, Gamepad2, Clock, TrendingUp } from 'lucide-react'
import { getTrendStats } from '../lib/api'
import { formatNumber } from '../lib/utils'

export function StatsBar() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['trendStats'],
    queryFn: getTrendStats,
    refetchInterval: 60000, // Refetch every minute
  })

  const statItems = [
    {
      icon: <Users className="w-5 h-5" />,
      label: 'Players Now',
      value: stats ? formatNumber(stats.total_players_now) : '-',
      color: 'text-aurora-gold',
    },
    {
      icon: <Gamepad2 className="w-5 h-5" />,
      label: 'Games Tracked',
      value: stats ? formatNumber(stats.total_games_tracked) : '-',
      color: 'text-aurora-cyan',
    },
    {
      icon: <TrendingUp className="w-5 h-5" />,
      label: 'Top Genre',
      value: stats?.top_genre || '-',
      color: 'text-aurora-purple',
    },
    {
      icon: <Clock className="w-5 h-5" />,
      label: 'Data Age',
      value: stats
        ? stats.data_freshness_hours < 0
          ? 'No data'
          : `${stats.data_freshness_hours.toFixed(1)}h`
        : '-',
      color: 'text-aurora-green',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {statItems.map((item, index) => (
        <motion.div
          key={item.label}
          className="stat-card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: index * 0.1 }}
        >
          {isLoading ? (
            <div className="animate-pulse">
              <div className="h-8 bg-aurora-cyan/20 rounded w-20 mb-2" />
              <div className="h-4 bg-aurora-cyan/10 rounded w-16" />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <span className={item.color}>{item.icon}</span>
              </div>
              <div className="stat-value">{item.value}</div>
              <div className="stat-label">{item.label}</div>
            </>
          )}
        </motion.div>
      ))}
    </div>
  )
}
