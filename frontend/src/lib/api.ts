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
