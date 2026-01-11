import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { getTrendingGames, getGenres } from '../lib/api'
import { GameCard } from './GameCard'
import { TrendChart } from './TrendChart'
import { Filter, RefreshCw } from 'lucide-react'

export function Dashboard() {
  const [selectedGenre, setSelectedGenre] = useState<string | undefined>()

  const {
    data: trendingData,
    isLoading: loadingTrends,
    refetch: refetchTrends,
    isFetching,
  } = useQuery({
    queryKey: ['trending', selectedGenre],
    queryFn: () => getTrendingGames({ limit: 20, genre: selectedGenre }),
    refetchInterval: 300000, // Refetch every 5 minutes
  })

  const { data: genresData } = useQuery({
    queryKey: ['genres'],
    queryFn: getGenres,
  })

  return (
    <div className="space-y-6">
      {/* Filters Row */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-aurora-deep-blue">
            Trending Games
          </h2>
          {trendingData?.last_updated && (
            <span className="text-xs text-aurora-deep-blue/50">
              Updated: {new Date(trendingData.last_updated).toLocaleTimeString()}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Genre Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-aurora-deep-blue/60" />
            <select
              value={selectedGenre || ''}
              onChange={(e) => setSelectedGenre(e.target.value || undefined)}
              className="bg-white/50 border border-aurora-cyan/30 rounded-lg px-3 py-1.5 text-sm
                         text-aurora-deep-blue focus:outline-none focus:ring-2 focus:ring-aurora-cyan/50"
            >
              <option value="">All Genres</option>
              {genresData?.genres.map((genre) => (
                <option key={genre.name} value={genre.name}>
                  {genre.name} ({genre.count})
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => refetchTrends()}
            disabled={isFetching}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw
              className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`}
            />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Games List - 2 columns */}
        <div className="lg:col-span-2 space-y-4">
          {loadingTrends ? (
            // Loading skeleton
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="glass-panel p-4 animate-pulse">
                  <div className="flex gap-4">
                    <div className="w-20 h-20 bg-aurora-cyan/20 rounded-lg" />
                    <div className="flex-1 space-y-2">
                      <div className="h-5 bg-aurora-cyan/20 rounded w-3/4" />
                      <div className="h-4 bg-aurora-cyan/10 rounded w-1/2" />
                      <div className="h-4 bg-aurora-cyan/10 rounded w-1/4" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : trendingData?.games.length === 0 ? (
            // Empty state
            <div className="glass-panel p-12 text-center">
              <p className="text-aurora-deep-blue/60 mb-4">
                No games found. Data may still be loading.
              </p>
              <button onClick={() => refetchTrends()} className="btn-aurora">
                Refresh Data
              </button>
            </div>
          ) : (
            // Games list
            <motion.div
              className="space-y-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              {trendingData?.games.map((game, index) => (
                <motion.div
                  key={game.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <GameCard game={game} />
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* Show total count */}
          {trendingData && trendingData.total > 0 && (
            <p className="text-sm text-aurora-deep-blue/50 text-center">
              Showing {trendingData.games.length} of {trendingData.total} games
            </p>
          )}
        </div>

        {/* Sidebar - Charts */}
        <div className="space-y-6">
          <TrendChart games={trendingData?.games || []} />

          {/* Genre Distribution */}
          {genresData && genresData.genres.length > 0 && (
            <div className="glass-panel p-4">
              <h3 className="font-semibold text-aurora-deep-blue mb-4">
                Genre Distribution
              </h3>
              <div className="space-y-2">
                {genresData.genres.slice(0, 8).map((genre) => (
                  <div key={genre.name} className="flex items-center gap-2">
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-aurora-deep-blue">{genre.name}</span>
                        <span className="text-aurora-deep-blue/60">{genre.count}</span>
                      </div>
                      <div className="h-2 bg-aurora-light rounded-full overflow-hidden">
                        <div
                          className="h-full bg-aurora-gradient rounded-full"
                          style={{
                            width: `${(genre.count / genresData.genres[0].count) * 100}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
