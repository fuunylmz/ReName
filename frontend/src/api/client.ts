export type MediaType = 'movie' | 'tv' | 'anime' | 'unknown';
export type MediaStatus =
  | 'discovered'
  | 'parsed'
  | 'matched'
  | 'needs_review'
  | 'planned'
  | 'completed'
  | 'failed'
  | 'ignored';

export interface MediaItem {
  id: number;
  source_path: string;
  raw_name: string;
  media_type: MediaType;
  status: MediaStatus;
  size: number;
  file_count: number;
  video_files: string[];
}

export interface ParsedResult {
  id: number;
  media_item_id: number;
  media_type: MediaType;
  title: string;
  original_title: string;
  year: number | null;
  season: number | null;
  episodes: Array<Record<string, unknown>>;
  quality: string;
  source: string;
  video_codec: string;
  audio: string;
  confidence: number;
}

export interface TmdbMatch {
  id: number;
  media_item_id: number;
  tmdb_id: number;
  media_type: MediaType;
  title: string;
  original_title: string;
  year: number | null;
  poster_path: string | null;
  overview: string;
  score: number;
  selected: boolean;
}

export interface RenamePlan {
  id: number;
  media_item_id: number;
  operation: 'hardlink' | 'copy' | 'move';
  status: string;
  plan: Array<{ source: string; target: string }>;
}

export interface AppSettings {
  tmdb_api_key: string;
  tmdb_language: string;
  llm_api_base_url: string;
  llm_api_key: string;
  llm_model: string;
  default_operation: string;
  movie_library_path: string;
  tv_library_path: string;
  anime_library_path: string;
  download_paths: string[];
}

export interface LLMModel {
  id: string;
  owned_by: string | null;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';

function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(url), {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? '请求失败');
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),
  getSettings: () => request<AppSettings>('/api/settings'),
  updateSettings: (settings: AppSettings) =>
    request<AppSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(settings) }),
  listLLMModels: (apiBaseUrl: string, apiKey: string) =>
    request<{ models: LLMModel[] }>('/api/llm/models', {
      method: 'POST',
      body: JSON.stringify({ api_base_url: apiBaseUrl, api_key: apiKey }),
    }),
  scan: (path: string, recursive = false) =>
    request<MediaItem[]>('/api/media-items/scan', {
      method: 'POST',
      body: JSON.stringify({ path, recursive }),
    }),
  listMediaItems: () => request<MediaItem[]>('/api/media-items'),
  parseMediaItem: (id: number) => request<ParsedResult>(`/api/media-items/${id}/parse`, { method: 'POST' }),
  parseMediaItemStreamUrl: (id: number) => apiUrl(`/api/media-items/${id}/parse-stream`),
  listParsedResults: (id: number) => request<ParsedResult[]>(`/api/media-items/${id}/parsed`),
  matchMediaItem: (id: number) => request<TmdbMatch[]>(`/api/media-items/${id}/match`, { method: 'POST' }),
  listMatches: (id: number) => request<TmdbMatch[]>(`/api/media-items/${id}/matches`),
  selectMatch: (itemId: number, matchId: number) =>
    request<TmdbMatch>(`/api/media-items/${itemId}/select-match`, {
      method: 'POST',
      body: JSON.stringify({ match_id: matchId }),
    }),
  createRenamePlan: (itemId: number, operation: 'hardlink' | 'copy' | 'move') =>
    request<RenamePlan>(`/api/media-items/${itemId}/rename-plan`, {
      method: 'POST',
      body: JSON.stringify({ operation }),
    }),
  executeRenamePlan: (planId: number) =>
    request<RenamePlan>(`/api/media-items/rename-plans/${planId}/execute`, { method: 'POST' }),
  listRenamePlans: (itemId: number) => request<RenamePlan[]>(`/api/media-items/${itemId}/rename-plans`),
};
