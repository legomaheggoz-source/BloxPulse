import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  DollarSign,
  TrendingUp,
  Package,
  Crown,
  Gem,
  Zap,
  Sparkles,
  ShoppingBag,
  RefreshCw,
} from 'lucide-react'
import { getMonetizationStats, getTopMonetizingGames } from '../lib/api'

// Price tier colors matching aurora theme
const TIER_COLORS = {
  budget: '#4DBD33',      // Green - affordable
  standard: '#00CED1',    // Cyan - normal
  premium: '#9370DB',     // Purple - premium
  luxury: '#FFD700',      // Gold - luxury
  whale: '#FF69B4',       // Pink - whale
}

// Pass type icons
const PASS_TYPE_ICONS: Record<string, React.ReactNode> = {
  vip: <Crown className="w-4 h-4" />,
  power: <Zap className="w-4 h-4" />,
  cosmetic: <Sparkles className="w-4 h-4" />,
  pack: <Package className="w-4 h-4" />,
  access: <Gem className="w-4 h-4" />,
  other: <ShoppingBag className="w-4 h-4" />,
}

export function Monetization() {
  const {
    data: stats,
    isLoading: loadingStats,
    refetch: refetchStats,
    isFetching,
  } = useQuery({
    queryKey: ['monetization-stats'],
    queryFn: getMonetizationStats,
    refetchInterval: 300000,
  })

  const { data: topGames, isLoading: loadingTop } = useQuery({
    queryKey: ['top-monetizing'],
    queryFn: () => getTopMonetizingGames(10),
    refetchInterval: 300000,
  })

  const formatRobux = (value: number) => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}k`
    }
    return value.toString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-aurora-deep-blue">
            Monetization Insights
          </h2>
          <span className="text-xs text-aurora-deep-blue/50">
            Game pass strategies & pricing analysis
          </span>
        </div>

        <button
          onClick={() => refetchStats()}
          disabled={isFetching}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {loadingStats ? (
        <div className="grid md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-panel p-4 animate-pulse">
              <div className="h-4 bg-aurora-cyan/20 rounded w-1/2 mb-2" />
              <div className="h-8 bg-aurora-cyan/20 rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : stats ? (
        <>
          {/* Overview Stats */}
          <div className="grid md:grid-cols-4 gap-4">
            <motion.div
              className="glass-panel p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center gap-2 text-aurora-deep-blue/60 text-sm mb-1">
                <Package className="w-4 h-4" />
                Total Passes
              </div>
              <div className="text-2xl font-bold text-aurora-deep-blue">
                {stats.total_passes.toLocaleString()}
              </div>
              <div className="text-xs text-aurora-deep-blue/50 mt-1">
                across {stats.games_with_passes} games
              </div>
            </motion.div>

            <motion.div
              className="glass-panel p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-center gap-2 text-aurora-deep-blue/60 text-sm mb-1">
                <DollarSign className="w-4 h-4" />
                Average Price
              </div>
              <div className="text-2xl font-bold text-aurora-gold">
                {Math.round(stats.avg_price)} R$
              </div>
              <div className="text-xs text-aurora-deep-blue/50 mt-1">
                per game pass
              </div>
            </motion.div>

            <motion.div
              className="glass-panel p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <div className="flex items-center gap-2 text-aurora-deep-blue/60 text-sm mb-1">
                <TrendingUp className="w-4 h-4" />
                Price Range
              </div>
              <div className="text-2xl font-bold text-aurora-deep-blue">
                {stats.price_range.min} - {formatRobux(stats.price_range.max)}
              </div>
              <div className="text-xs text-aurora-deep-blue/50 mt-1">
                Robux
              </div>
            </motion.div>

            <motion.div
              className="glass-panel p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <div className="flex items-center gap-2 text-aurora-deep-blue/60 text-sm mb-1">
                <Gem className="w-4 h-4" />
                Passes/Game
              </div>
              <div className="text-2xl font-bold text-aurora-purple">
                {(stats.total_passes / Math.max(stats.games_with_passes, 1)).toFixed(1)}
              </div>
              <div className="text-xs text-aurora-deep-blue/50 mt-1">
                average
              </div>
            </motion.div>
          </div>

          {/* Main Content Grid */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Price Tier Distribution */}
            <motion.div
              className="glass-panel p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <h3 className="font-semibold text-aurora-deep-blue mb-4">
                Price Tier Distribution
              </h3>
              <div className="space-y-3">
                {Object.entries(stats.price_tiers).map(([tier, count]) => {
                  const total = Object.values(stats.price_tiers).reduce((a, b) => a + b, 0)
                  const percent = total > 0 ? (count / total) * 100 : 0
                  const labels: Record<string, string> = {
                    budget: 'Budget (<50 R$)',
                    standard: 'Standard (50-199 R$)',
                    premium: 'Premium (200-499 R$)',
                    luxury: 'Luxury (500-999 R$)',
                    whale: 'Whale (1000+ R$)',
                  }
                  return (
                    <div key={tier}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-aurora-deep-blue">{labels[tier] || tier}</span>
                        <span className="text-aurora-deep-blue/60">
                          {count} ({percent.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="h-3 bg-aurora-light rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{
                            backgroundColor: TIER_COLORS[tier as keyof typeof TIER_COLORS] || '#888',
                          }}
                          initial={{ width: 0 }}
                          animate={{ width: `${percent}%` }}
                          transition={{ duration: 0.5, delay: 0.1 }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </motion.div>

            {/* Pass Type Breakdown */}
            <motion.div
              className="glass-panel p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <h3 className="font-semibold text-aurora-deep-blue mb-4">
                Pass Type Breakdown
              </h3>
              <div className="space-y-3">
                {stats.pass_types.slice(0, 8).map((type) => (
                  <div
                    key={type.type}
                    className="flex items-center justify-between p-2 rounded-lg bg-aurora-light/50"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-aurora-cyan">
                        {PASS_TYPE_ICONS[type.type] || PASS_TYPE_ICONS.other}
                      </span>
                      <span className="text-aurora-deep-blue capitalize">
                        {type.type}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-aurora-deep-blue">
                        {type.count} passes
                      </div>
                      <div className="text-xs text-aurora-deep-blue/60">
                        avg {Math.round(type.avg_price)} R$
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Top Monetizing Games */}
            <motion.div
              className="glass-panel p-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <h3 className="font-semibold text-aurora-deep-blue mb-4">
                Top Monetizing Games
              </h3>
              {loadingTop ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-12 bg-aurora-cyan/10 rounded animate-pulse" />
                  ))}
                </div>
              ) : topGames && topGames.length > 0 ? (
                <div className="space-y-2">
                  {topGames.slice(0, 8).map((game, index) => (
                    <div
                      key={game.game_id}
                      className="flex items-center gap-3 p-2 rounded-lg bg-aurora-light/50"
                    >
                      <span className="text-aurora-deep-blue/40 text-sm w-5">
                        #{index + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-aurora-deep-blue truncate">
                          {game.game_name}
                        </div>
                        <div className="text-xs text-aurora-deep-blue/60">
                          {game.pass_count} passes
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-aurora-gold">
                          {formatRobux(game.total_value)} R$
                        </div>
                        <div className="text-xs text-aurora-deep-blue/50">
                          total value
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-aurora-deep-blue/50 py-8">
                  No monetization data available
                </div>
              )}
            </motion.div>
          </div>

          {/* How to Use This Data */}
          <motion.div
            className="glass-panel p-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
          >
            <h3 className="font-semibold text-aurora-deep-blue mb-4">
              How to Use This Data
            </h3>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <h4 className="font-medium text-aurora-deep-blue">Reading the Charts</h4>
                <ul className="space-y-2 text-sm text-aurora-deep-blue/80">
                  <li className="flex gap-2">
                    <span className="text-aurora-gold">•</span>
                    <span><strong>Price Tiers</strong> - Most passes are {stats.price_tiers.premium > stats.price_tiers.standard ? 'Premium (200-499 R$)' : 'Standard (50-199 R$)'}. Price your core passes here for best conversion.</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-aurora-cyan">•</span>
                    <span><strong>Pass Types</strong> - "{stats.pass_types[0]?.type}" dominates, but differentiate by focusing on underserved types like "{stats.pass_types.slice(-2)[0]?.type || 'utility'}".</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-aurora-purple">•</span>
                    <span><strong>Top Monetizers</strong> - High total value comes from MANY passes, not expensive ones. Quantity at reasonable prices wins.</span>
                  </li>
                </ul>
              </div>
              <div className="space-y-4">
                <h4 className="font-medium text-aurora-deep-blue">Your Monetization Playbook</h4>
                <div className="space-y-3">
                  <div className="p-3 bg-aurora-green/10 border border-aurora-green/30 rounded-lg">
                    <div className="text-sm font-medium text-aurora-green">ESSENTIAL: VIP Pass</div>
                    <div className="text-sm text-aurora-deep-blue/80 mt-1">
                      Price at {Math.round(stats.avg_price * 0.8)} - {Math.round(stats.avg_price * 1.2)} R$ (market avg: {Math.round(stats.avg_price)} R$). Include 3-5 perks minimum.
                    </div>
                  </div>
                  <div className="p-3 bg-aurora-gold/10 border border-aurora-gold/30 rounded-lg">
                    <div className="text-sm font-medium text-aurora-gold">WHALE BAIT: Premium Tier</div>
                    <div className="text-sm text-aurora-deep-blue/80 mt-1">
                      Add 1-2 passes at 1000+ R$ for completionists. Only {stats.price_tiers.whale} passes ({((stats.price_tiers.whale / stats.total_passes) * 100).toFixed(1)}%) are whale-tier - low competition.
                    </div>
                  </div>
                  <div className="p-3 bg-aurora-cyan/10 border border-aurora-cyan/30 rounded-lg">
                    <div className="text-sm font-medium text-aurora-cyan">VOLUME: {(stats.total_passes / Math.max(stats.games_with_passes, 1)).toFixed(0)} passes average</div>
                    <div className="text-sm text-aurora-deep-blue/80 mt-1">
                      Target 5-10 passes: VIP, 2-3 cosmetics, 1-2 power/utility, 1 whale option. Total potential spend: {Math.round(stats.avg_price * 7)} R$.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      ) : (
        <div className="glass-panel p-12 text-center">
          <p className="text-aurora-deep-blue/60 mb-4">
            No monetization data available yet.
          </p>
          <button onClick={() => refetchStats()} className="btn-aurora">
            Refresh Data
          </button>
        </div>
      )}
    </div>
  )
}
