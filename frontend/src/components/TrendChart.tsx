import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { GameSummary } from '../lib/api'
import { formatNumber, truncate } from '../lib/utils'

interface TrendChartProps {
  games: GameSummary[]
}

export function TrendChart({ games }: TrendChartProps) {
  // Take top 10 games for the chart
  const chartData = games.slice(0, 10).map((game) => ({
    name: truncate(game.name, 15),
    fullName: game.name,
    playing: game.playing,
    id: game.id,
  }))

  // Aurora gradient colors for bars
  const colors = [
    '#FFD700', // Gold
    '#FFD700',
    '#00CED1', // Cyan
    '#00CED1',
    '#00CED1',
    '#9370DB', // Purple
    '#9370DB',
    '#9370DB',
    '#9370DB',
    '#9370DB',
  ]

  if (chartData.length === 0) {
    return (
      <div className="glass-panel p-4">
        <h3 className="font-semibold text-aurora-deep-blue mb-4">
          Top Games by Players
        </h3>
        <div className="h-64 flex items-center justify-center text-aurora-deep-blue/50">
          No data available
        </div>
      </div>
    )
  }

  return (
    <div className="glass-panel p-4">
      <h3 className="font-semibold text-aurora-deep-blue mb-4">
        Top Games by Current Players
      </h3>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 5, bottom: 5 }}
          >
            <XAxis
              type="number"
              tickFormatter={(value) => formatNumber(value)}
              tick={{ fill: '#001a4d', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(0, 206, 209, 0.2)' }}
              tickLine={{ stroke: 'rgba(0, 206, 209, 0.2)' }}
            />
            <YAxis
              dataKey="name"
              type="category"
              width={80}
              tick={{ fill: '#001a4d', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(0, 206, 209, 0.2)' }}
              tickLine={false}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: 'rgba(0, 206, 209, 0.1)' }}
            />
            <Bar dataKey="playing" radius={[0, 4, 4, 0]}>
              {chartData.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={colors[index] || colors[colors.length - 1]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null

  const data = payload[0].payload

  return (
    <div className="bg-white/95 backdrop-blur-sm border border-aurora-cyan/30 rounded-lg p-3 shadow-aurora">
      <p className="font-medium text-aurora-deep-blue text-sm">{data.fullName}</p>
      <p className="text-aurora-cyan font-semibold">
        {formatNumber(data.playing)} playing
      </p>
    </div>
  )
}
