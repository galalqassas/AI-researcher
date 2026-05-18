const API_BASE = import.meta.env.VITE_API_URL || '';

const CACHE_PREFIX = 'ar_cache:';

function cacheGet<T>(key: string): T | undefined {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + key);
    if (raw == null) return undefined;
    return JSON.parse(raw) as T;
  } catch {
    return undefined;
  }
}

function cacheSet<T>(key: string, value: T): void {
  try {
    localStorage.setItem(CACHE_PREFIX + key, JSON.stringify(value));
  } catch { /* full or unavailable */ }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': '1',
    },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

/**
 * Wraps a fetcher with localStorage caching.
 * On network / 5xx failure, returns cached data if available instead of throwing.
 * 4xx errors always re-throw. Pass `cacheKey=null` to skip caching (e.g. POST).
 */
async function cachedFetch<T>(
  cacheKey: string | null,
  fetcher: () => Promise<T>,
): Promise<{ data: T; fromCache: boolean }> {
  try {
    const data = await fetcher();
    if (cacheKey) cacheSet(cacheKey, data);
    return { data, fromCache: false };
  } catch (err: any) {
    const offline = (err instanceof TypeError || err?.message?.includes('Failed to fetch'))
      || /API [5-9]\d\d/.test(err?.message ?? '');
    if (cacheKey && offline) {
      const cached = cacheGet<T>(cacheKey);
      if (cached !== undefined) return { data: cached, fromCache: true };
    }
    throw err;
  }
}

/** Cached GET wrapper. */
function cachedGet<T>(cacheKey: string, path: string): Promise<{ data: T; fromCache: boolean }> {
  return cachedFetch<T>(cacheKey, () => apiFetch<T>(path));
}

// ── Types ──────────────────────────────────────────────────────────────────

export type BucketKey = 'general_ai' | 'autonomous_agents' | 'ai_finance';

export interface Paper {
  id: number;
  arxiv_id: string;
  title: string;
  authors: string | null;
  abstract: string | null;
  published_date: string | null;
  ingested_at: string | null;
  buckets: BucketKey[];
}

export interface PipelineRun {
  id: number;
  name: string;
  started_at: string;
  finished_at: string | null;
  duration_s: number | null;
  status: 'success' | 'error' | 'running';
  paper_count: number | null;
  stages: Record<string, number> | null;
  error: string | null;
}

export interface Report {
  id: number;
  period: string;
  generated_at: string;
  paper_count: number;
  content_html: string;
}

export interface PaperStats {
  total: number;
  today: number;
  per_bucket: Record<string, number>;
  per_date: { date: string; count: number; general_ai: number; autonomous_agents: number; ai_finance: number }[];
}

export interface SearchResult {
  id: number;
  arxiv_id: string;
  title: string;
  abstract: string;
  published_date: string | null;
  buckets: BucketKey[];
  score: number;
}

export const BUCKET_CONFIG = {
  general_ai: {
    label: 'General AI',
    color: '#6366F1',
    colorLight: '#EEF2FF',
    shadow: '#6366F1',
    gradientFrom: '#818CF8',
    gradientTo: '#6366F1',
    categories: ['cs.AI', 'cs.LG'],
  },
  autonomous_agents: {
    label: 'Autonomous Agents',
    color: '#10B981',
    colorLight: '#ECFDF5',
    shadow: '#10B981',
    gradientFrom: '#34D399',
    gradientTo: '#059669',
    categories: ['cs.MA', 'cs.AI'],
  },
  ai_finance: {
    label: 'AI × Finance',
    color: '#F59E0B',
    colorLight: '#FFFBEB',
    shadow: '#F59E0B',
    gradientFrom: '#FCD34D',
    gradientTo: '#D97706',
    categories: ['q-fin.ST', 'q-fin.CP', 'q-fin.GN'],
  },
} as const;

// ── API functions ───────────────────────────────────────────────────────────

export interface CachedResult<T> { data: T; fromCache: boolean }

export async function fetchPapers(bucket?: string, page = 1, limit = 50, search?: string): Promise<CachedResult<{ total: number; results: Paper[] }>> {
  const params = new URLSearchParams();
  if (bucket) params.set('bucket', bucket);
  if (search) params.set('search', search);
  params.set('page', String(page));
  params.set('limit', String(limit));
  const qs = params.toString();
  return cachedGet(`papers:${qs}`, `/papers?${qs}`);
}

export async function fetchPaperStats(): Promise<CachedResult<PaperStats>> {
  return cachedGet('paper_stats', '/papers/stats');
}

export async function fetchPipelineRuns(limit = 20): Promise<CachedResult<PipelineRun[]>> {
  return cachedGet(`pipeline_runs:${limit}`, `/pipeline-runs?limit=${limit}`);
}

export async function fetchReports(): Promise<CachedResult<Report[]>> {
  return cachedGet('reports', '/reports');
}

export async function fetchReport(id: number): Promise<CachedResult<Report>> {
  return cachedGet(`report:${id}`, `/reports/${id}`);
}

export async function searchPapers(query: string, limit = 10): Promise<CachedResult<{ query: string; results: SearchResult[] }>> {
  return cachedGet(`search:${query}:${limit}`, `/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function runPipeline(): Promise<{ status: string; paper_count: number; stages: Record<string, number> }> {
  return cachedFetch(null, () => apiFetch('/ingest', { method: 'POST' })).then(r => r.data);
}

export async function generateReport(period: string): Promise<{ id: number; period: string; paper_count: number }> {
  return cachedFetch(null, () => apiFetch(`/reports/generate?period=${period}`, { method: 'POST' })).then(r => r.data);
}