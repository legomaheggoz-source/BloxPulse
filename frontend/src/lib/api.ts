/**
 * BloxPulse API Client
 *
 * Handles all API requests to the backend.
 */

const API_BASE = '/api/v1'

/**
 * Fetch wrapper with error handling
 */
async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

// =============================================================================
// Types
// =============================================================================

export interface GameSummary {
  id: number
  name: string
  creator_name: string | null
  playing: number
  visits: number
  favorites: number
  genre: string | null
  thumbnail_url: string | null
  trending_rank: number | null
  updated_at: string
}

export interface TrendingResponse {
  games: GameSummary[]
  total: number
  last_updated: string | null
}

export interface TrendStats {
  total_games_tracked: number
  total_players_now: number
  average_players: number
  top_genre: string | null
  data_freshness_hours: number
}

export interface GameDetail extends GameSummary {
  description: string | null
  creator_id: number | null
  created_at: string
  roblox_url: string
}

export interface HealthResponse {
  status: string
  timestamp: string
  environment: string
  database: string
  version: string
}

export interface Genre {
  name: string
  count: number
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get trending games
 */
export async function getTrendingGames(params?: {
  limit?: number
  offset?: number
  genre?: string
}): Promise<TrendingResponse> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.offset) searchParams.set('offset', params.offset.toString())
  if (params?.genre) searchParams.set('genre', params.genre)

  const query = searchParams.toString()
  return fetchApi<TrendingResponse>(`/trends${query ? `?${query}` : ''}`)
}

/**
 * Get trend statistics
 */
export async function getTrendStats(): Promise<TrendStats> {
  return fetchApi<TrendStats>('/trends/stats')
}

/**
 * Get available genres
 */
export async function getGenres(): Promise<{ genres: Genre[] }> {
  return fetchApi<{ genres: Genre[] }>('/trends/genres')
}

/**
 * Get game details
 */
export async function getGame(gameId: number): Promise<GameDetail> {
  return fetchApi<GameDetail>(`/games/${gameId}`)
}

/**
 * Search games
 */
export async function searchGames(query: string, limit = 20): Promise<GameSummary[]> {
  return fetchApi<GameSummary[]>(`/games?q=${encodeURIComponent(query)}&limit=${limit}`)
}

/**
 * Get game trend history
 */
export async function getGameHistory(
  gameId: number,
  hours = 24
): Promise<{
  game_id: number
  game_name: string
  hours: number
  snapshots: Array<{
    timestamp: string
    playing: number
    visits: number
    favorites: number
    trending_rank: number | null
  }>
}> {
  return fetchApi(`/trends/history/${gameId}?hours=${hours}`)
}

/**
 * Health check
 */
export async function getHealth(): Promise<HealthResponse> {
  return fetchApi<HealthResponse>('/health')
}

/**
 * Trigger manual data collection (admin)
 */
export async function triggerCollection(): Promise<{ status: string }> {
  return fetchApi<{ status: string }>('/admin/collect', { method: 'POST' })
}

/**
 * Refresh data - triggers collection with status
 */
export interface RefreshResponse {
  status: string
  message: string
  games_in_list: number
  note: string
}

export async function refreshData(): Promise<RefreshResponse> {
  return fetchApi<RefreshResponse>('/admin/refresh', { method: 'POST' })
}

// =============================================================================
// Monetization Types & Functions
// =============================================================================

export interface MonetizationStats {
  total_passes: number
  games_with_passes: number
  avg_price: number
  price_range: {
    min: number
    max: number
  }
  price_tiers: {
    budget: number
    standard: number
    premium: number
    luxury: number
    whale: number
  }
  pass_types: Array<{
    type: string
    count: number
    avg_price: number
  }>
}

export interface GamePassDetail {
  id: number
  name: string
  price: number | null
  pass_type: string | null
  is_for_sale: boolean
}

export interface GameMonetization {
  game_id: number
  game_name: string
  pass_count: number
  total_value: number
  avg_price: number
  passes: GamePassDetail[]
}

/**
 * Get monetization statistics
 */
export async function getMonetizationStats(): Promise<MonetizationStats> {
  return fetchApi<MonetizationStats>('/monetization/stats')
}

/**
 * Get monetization data for a specific game
 */
export async function getGameMonetization(gameId: number): Promise<GameMonetization> {
  return fetchApi<GameMonetization>(`/monetization/game/${gameId}`)
}

/**
 * Get top monetizing games
 */
export async function getTopMonetizingGames(limit = 10): Promise<GameMonetization[]> {
  return fetchApi<GameMonetization[]>(`/monetization/top?limit=${limit}`)
}

// =============================================================================
// Zetta Export Types & Functions
// =============================================================================

export interface ZettaExport {
  schema_version: string
  export_timestamp: string
  data_freshness_hours: number
  summary: {
    total_games_tracked: number
    total_concurrent_players: number
    unique_genres: number
    tier_distribution: Record<string, number>
    market_concentration: {
      top_5_share_percent: number
      top_10_share_percent: number
    }
  }
  games: Array<{
    universe_id: number
    name: string
    creator: string | null
    genre: string | null
    metrics: {
      current_players: number
      total_visits: number
      favorites: number
    }
    popularity_score: number
    engagement_score: number
    tier: string
  }>
  genres: Array<{
    name: string
    game_count: number
    total_ccu: number
    avg_ccu_per_game: number
    market_share_percent: number
    saturation_level: string
    top_games: string[]
  }>
  monetization: {
    total_passes_tracked: number
    games_with_passes: number
    avg_passes_per_game: number
    overall_avg_price: number
    price_tier_distribution: Record<string, number>
    pass_type_popularity: Array<{ type: string; count: number; percent: number }>
    genre_monetization: Array<{ genre: string; avg_price: number; pass_count: number }>
    top_strategies: string[]
  } | null
  game_monetization: Array<{
    game_id: number
    game_name: string
    strategy: {
      pass_count: number
      price_range: [number, number]
      avg_price: number
      total_potential_spend: number
      pass_type_breakdown: Record<string, number>
      pricing_tier: string
    } | null
    passes: Array<{ name: string; price: number; type: string }>
  }>
  opportunities: Array<{
    opportunity_type: string
    description: string
    confidence: number
    supporting_data: Record<string, unknown>
    recommended_action: string
  }>
  recommendations: {
    recommended_genres: string[]
    genre_reasoning: Record<string, string>
    successful_patterns: Record<string, unknown>
    avoid_list: string[]
    key_insights: string[]
  }
}

/**
 * Get full Zetta export
 */
export async function getZettaExport(): Promise<ZettaExport> {
  return fetchApi<ZettaExport>('/export/zetta')
}

/**
 * Download Zetta export as JSON file
 */
export async function downloadZettaExport(): Promise<void> {
  const data = await getZettaExport()
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `bloxpulse-zetta-export-${new Date().toISOString().split('T')[0]}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
