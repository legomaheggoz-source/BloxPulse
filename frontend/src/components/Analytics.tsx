import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from 'recharts'
import { TrendingUp, TrendingDown, Activity, Users, BarChart2, PieChartIcon } from 'lucide-react'
import { getTrendStats, getGenres, getTrendingGames } from '../lib/api'

// Aurora theme colors for charts
const CHART_COLORS = [
  '#FFD700', // Gold
  '#00CED1', // Cyan
  '#9370DB', // Purple
  '#FFA500', // Orange
  '#4DBD33', // Green
  '#FF69B4', // Pink
  '#87CEEB', // Sky Blue
  '#DDA0DD', // Plum
]

export function Analytics() {
  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ['trend-stats'],
    queryFn: getTrendStats,
  })

  const { data: genresData, isLoading: loadingGenres } = useQuery({
    queryKey: ['genres'],
    queryFn: getGenres,
  })

  const { data: trendingData, isLoading: loadingTrends } = useQuery({
    queryKey: ['trending-all'],
    queryFn: () => getTrendingGames({ limit: 50 }),
  })

  // Transform genres data for pie chart
  const genrePieData = genresData?.genres.slice(0, 8).map((g, i) => ({
    name: g.name,
    value: g.count,
    color: CHART_COLORS[i % CHART_COLORS.length],
  })) || []

  // Transform games data for bar chart (top 10 by players)
  const topGamesData = trendingData?.games.slice(0, 10).map((g) => ({
    name: g.name.length > 15 ? g.name.substring(0, 15) + '...' : g.name,
    players: g.playing,
    visits: g.visits / 1000000, // Convert to millions
  })) || []

  // Calculate tier distribution
  const tierData = trendingData ? [
    { name: '100k+', count: trendingData.games.filter(g => g.playing >= 100000).length, color: '#FFD700' },
    { name: '20k-100k', count: trendingData.games.filter(g => g.playing >= 20000 && g.playing < 100000).length, color: '#00CED1' },
    { name: '5k-20k', count: trendingData.games.filter(g => g.playing >= 5000 && g.playing < 20000).length, color: '#9370DB' },
    { name: '1k-5k', count: trendingData.games.filter(g => g.playing >= 1000 && g.playing < 5000).length, color: '#FFA500' },
    { name: '<1k', count: trendingData.games.filter(g => g.playing < 1000).length, color: '#4DBD33' },
  ] : []

  const isLoading = loadingStats || loadingGenres || loadingTrends

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-aurora-deep-blue flex items-center gap-2">
          <Activity className="w-5 h-5 text-aurora-cyan" />
          Market Analytics
        </h2>
        {stats && (
          <span className="text-xs text-aurora-deep-blue/50">
            Data freshness: {stats.data_freshness_hours >= 0
              ? `${stats.data_freshness_hours.toFixed(1)} hours ago`
              : 'Unknown'}
          </span>
        )}
      </div>

      {/* Stats Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total CCU"
          value={stats?.total_players_now.toLocaleString() || '-'}
          icon={<Users className="w-5 h-5" />}
          loading={loadingStats}
          color="gold"
        />
        <StatCard
          title="Games Tracked"
          value={stats?.total_games_tracked.toString() || '-'}
          icon={<BarChart2 className="w-5 h-5" />}
          loading={loadingStats}
          color="cyan"
        />
        <StatCard
          title="Avg Players/Game"
          value={stats?.average_players
            ? Math.round(stats.average_players).toLocaleString()
            : '-'}
          icon={<Activity className="w-5 h-5" />}
          loading={loadingStats}
          color="purple"
        />
        <StatCard
          title="Top Genre"
          value={stats?.top_genre || '-'}
          icon={<PieChartIcon className="w-5 h-5" />}
          loading={loadingStats}
          color="orange"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Games by CCU */}
        <motion.div
          className="glass-panel p-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <h3 className="font-semibold text-aurora-deep-blue mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-aurora-gold" />
            Top Games by Current Players
          </h3>
          {isLoading ? (
            <div className="h-64 bg-aurora-light/50 animate-pulse rounded-lg" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={topGamesData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#00CED120" />
                <XAxis type="number" tick={{ fill: '#001a4d', fontSize: 12 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: '#001a4d', fontSize: 11 }}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid rgba(0, 206, 209, 0.3)',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number) => [value.toLocaleString(), 'Players']}
                />
                <Bar dataKey="players" fill="url(#goldGradient)" radius={[0, 4, 4, 0]} />
                <defs>
                  <linearGradient id="goldGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#FFD700" />
                    <stop offset="100%" stopColor="#FFA500" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Genre Distribution Pie Chart */}
        <motion.div
          className="glass-panel p-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <h3 className="font-semibold text-aurora-deep-blue mb-4 flex items-center gap-2">
            <PieChartIcon className="w-4 h-4 text-aurora-purple" />
            Genre Distribution
          </h3>
          {isLoading ? (
            <div className="h-64 bg-aurora-light/50 animate-pulse rounded-lg" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={genrePieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {genrePieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid rgba(0, 206, 209, 0.3)',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, name: string) => [
                    `${value} games`,
                    name,
                  ]}
                />
                <Legend
                  layout="vertical"
                  align="right"
                  verticalAlign="middle"
                  iconType="circle"
                  formatter={(value) => (
                    <span className="text-sm text-aurora-deep-blue">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Player Tier Distribution */}
        <motion.div
          className="glass-panel p-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          <h3 className="font-semibold text-aurora-deep-blue mb-4 flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-aurora-cyan" />
            Games by Player Count Tier
          </h3>
          {isLoading ? (
            <div className="h-64 bg-aurora-light/50 animate-pulse rounded-lg" />
          ) : (
            <div className="space-y-4">
              {tierData.map((tier) => (
                <div key={tier.name} className="flex items-center gap-3">
                  <span className="text-sm text-aurora-deep-blue w-20">{tier.name}</span>
                  <div className="flex-1 h-8 bg-aurora-light rounded-lg overflow-hidden">
                    <motion.div
                      className="h-full rounded-lg flex items-center justify-end pr-2"
                      style={{ backgroundColor: tier.color }}
                      initial={{ width: 0 }}
                      animate={{
                        width: `${Math.max(10, (tier.count / (trendingData?.games.length || 1)) * 100)}%`
                      }}
                      transition={{ duration: 0.5 }}
                    >
                      <span className="text-sm font-medium text-white drop-shadow">
                        {tier.count}
                      </span>
                    </motion.div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Market Insights */}
        <motion.div
          className="glass-panel p-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
        >
          <h3 className="font-semibold text-aurora-deep-blue mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-aurora-green" />
            Market Insights
          </h3>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-16 bg-aurora-light/50 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              <InsightCard
                title="Market Concentration"
                value={`${((topGamesData.slice(0, 5).reduce((sum, g) => sum + g.players, 0) / (stats?.total_players_now || 1)) * 100).toFixed(1)}%`}
                description="Top 5 games share of total CCU"
                trend="neutral"
              />
              <InsightCard
                title="Genre Diversity"
                value={genresData?.genres.length.toString() || '0'}
                description="Unique genres in tracked games"
                trend="up"
              />
              <InsightCard
                title="Average Tier"
                value={trendingData ?
                  (trendingData.games.reduce((sum, g) => sum + g.playing, 0) / trendingData.games.length > 20000 ? 'High' : 'Medium')
                  : '-'}
                description="Based on average CCU across all games"
                trend="up"
              />
              <InsightCard
                title="Data Coverage"
                value={stats?.total_games_tracked.toString() || '0'}
                description="Games actively monitored"
                trend="neutral"
              />
            </div>
          )}
        </motion.div>
      </div>

      {/* Historical Note */}
      <div className="glass-panel p-4 text-center">
        <p className="text-sm text-aurora-deep-blue/60">
          Historical trend charts will become available after 24+ hours of data collection.
          Data is collected every 6 hours.
        </p>
      </div>
    </div>
  )
}

// Helper Components
function StatCard({
  title,
  value,
  icon,
  loading,
  color,
}: {
  title: string
  value: string
  icon: React.ReactNode
  loading: boolean
  color: 'gold' | 'cyan' | 'purple' | 'orange'
}) {
  const colorClasses = {
    gold: 'text-aurora-gold',
    cyan: 'text-aurora-cyan',
    purple: 'text-aurora-purple',
    orange: 'text-aurora-orange',
  }

  return (
    <motion.div
      className="glass-panel p-4"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className={colorClasses[color]}>{icon}</span>
        <span className="text-xs text-aurora-deep-blue/60">{title}</span>
      </div>
      {loading ? (
        <div className="h-7 bg-aurora-light/50 animate-pulse rounded" />
      ) : (
        <p className="text-xl font-bold text-aurora-deep-blue">{value}</p>
      )}
    </motion.div>
  )
}

function InsightCard({
  title,
  value,
  description,
  trend,
}: {
  title: string
  value: string
  description: string
  trend: 'up' | 'down' | 'neutral'
}) {
  return (
    <div className="flex items-center gap-3 p-3 bg-aurora-light/30 rounded-lg">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
        trend === 'up' ? 'bg-aurora-green/20' :
        trend === 'down' ? 'bg-red-100' :
        'bg-aurora-cyan/20'
      }`}>
        {trend === 'up' ? (
          <TrendingUp className="w-5 h-5 text-aurora-green" />
        ) : trend === 'down' ? (
          <TrendingDown className="w-5 h-5 text-red-500" />
        ) : (
          <Activity className="w-5 h-5 text-aurora-cyan" />
        )}
      </div>
      <div className="flex-1">
        <div className="flex items-baseline gap-2">
          <span className="font-semibold text-aurora-deep-blue">{value}</span>
          <span className="text-sm text-aurora-deep-blue/60">{title}</span>
        </div>
        <p className="text-xs text-aurora-deep-blue/50">{description}</p>
      </div>
    </div>
  )
}
