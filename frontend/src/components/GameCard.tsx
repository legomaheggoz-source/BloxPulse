import { motion } from 'framer-motion'
import { Users, Eye, Heart, ExternalLink, Trophy } from 'lucide-react'
import type { GameSummary } from '../lib/api'
import { formatNumber, getRankColor, truncate } from '../lib/utils'

interface GameCardProps {
  game: GameSummary
}

export function GameCard({ game }: GameCardProps) {
  const robloxUrl = `https://www.roblox.com/games/${game.id}`

  return (
    <motion.div
      className="glass-panel p-4 hover:shadow-aurora-lg transition-all duration-300 group"
      whileHover={{ scale: 1.01 }}
    >
      <div className="flex gap-4">
        {/* Thumbnail */}
        <div className="relative flex-shrink-0">
          {game.thumbnail_url ? (
            <img
              src={game.thumbnail_url}
              alt={game.name}
              className="w-20 h-20 rounded-lg object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-20 h-20 rounded-lg bg-aurora-gradient flex items-center justify-center">
              <span className="text-2xl font-bold text-aurora-deep-blue">
                {game.name.charAt(0)}
              </span>
            </div>
          )}

          {/* Rank Badge */}
          {game.trending_rank && game.trending_rank <= 10 && (
            <div className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-aurora-gold flex items-center justify-center shadow-gold">
              <Trophy className="w-3 h-3 text-aurora-deep-blue" />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-semibold text-aurora-deep-blue truncate group-hover:text-aurora-cyan transition-colors">
                {truncate(game.name, 40)}
              </h3>
              {game.creator_name && (
                <p className="text-sm text-aurora-deep-blue/60 truncate">
                  by {game.creator_name}
                </p>
              )}
            </div>

            {/* Rank */}
            {game.trending_rank && (
              <span
                className={`flex-shrink-0 text-lg font-bold ${getRankColor(
                  game.trending_rank
                )}`}
              >
                #{game.trending_rank}
              </span>
            )}
          </div>

          {/* Stats Row */}
          <div className="flex flex-wrap items-center gap-4 mt-3">
            <StatBadge
              icon={<Users className="w-3.5 h-3.5" />}
              value={formatNumber(game.playing)}
              label="playing"
              highlight
            />
            <StatBadge
              icon={<Eye className="w-3.5 h-3.5" />}
              value={formatNumber(game.visits)}
              label="visits"
            />
            <StatBadge
              icon={<Heart className="w-3.5 h-3.5" />}
              value={formatNumber(game.favorites)}
              label="favorites"
            />

            {game.genre && <span className="badge-genre">{game.genre}</span>}
          </div>
        </div>

        {/* Actions */}
        <div className="flex-shrink-0 flex items-center">
          <a
            href={robloxUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg text-aurora-deep-blue/40 hover:text-aurora-cyan
                       hover:bg-aurora-cyan/10 transition-all"
            title="Open in Roblox"
          >
            <ExternalLink className="w-5 h-5" />
          </a>
        </div>
      </div>
    </motion.div>
  )
}

function StatBadge({
  icon,
  value,
  label,
  highlight = false,
}: {
  icon: React.ReactNode
  value: string
  label: string
  highlight?: boolean
}) {
  return (
    <div
      className={`flex items-center gap-1.5 text-sm ${
        highlight ? 'text-aurora-cyan font-medium' : 'text-aurora-deep-blue/60'
      }`}
    >
      {icon}
      <span>{value}</span>
      <span className="text-aurora-deep-blue/40 text-xs">{label}</span>
    </div>
  )
}
