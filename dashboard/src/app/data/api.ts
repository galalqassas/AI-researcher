const API_BASE = import.meta.env.VITE_API_URL || '';

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
  per_bucket: Record<string, number>;
  per_date: { month: string; count: number; general_ai: number; autonomous_agents: number; ai_finance: number }[];
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

export async function fetchPapers(bucket?: string, page = 1, limit = 50): Promise<{ total: number; results: Paper[] }> {
  const params = new URLSearchParams();
  if (bucket) params.set('bucket', bucket);
  params.set('page', String(page));
  params.set('limit', String(limit));
  return apiFetch(`/papers?${params}`);
}

export async function fetchPaperStats(): Promise<PaperStats> {
  return apiFetch('/papers/stats');
}

export async function fetchPipelineRuns(limit = 20): Promise<PipelineRun[]> {
  return apiFetch(`/pipeline-runs?limit=${limit}`);
}

export async function fetchReports(): Promise<Report[]> {
  return apiFetch('/reports');
}

export async function fetchReport(id: number): Promise<Report> {
  return apiFetch(`/reports/${id}`);
}

export async function searchPapers(query: string, limit = 10): Promise<{ query: string; results: SearchResult[] }> {
  return apiFetch(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function runPipeline(): Promise<{ status: string; paper_count: number; stages: Record<string, number> }> {
  return apiFetch('/ingest', { method: 'POST' });
}

export async function generateReport(period: string): Promise<{ id: number; period: string; paper_count: number }> {
  return apiFetch(`/reports/generate?period=${period}`, { method: 'POST' });
}