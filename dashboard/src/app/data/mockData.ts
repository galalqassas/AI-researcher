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

export type BucketKey = keyof typeof BUCKET_CONFIG;

export interface Paper {
  id: number;
  arxiv_id: string;
  title: string;
  authors: string;
  abstract: string;
  published_date: string;
  ingested_at: string;
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
  stages: { ingested?: number; deduplicated?: number; embedded?: number; classified?: number } | null;
  error: string | null;
}

export interface Report {
  id: number;
  period: string;
  generated_at: string;
  paper_count: number;
  content_html: string;
}

export const MOCK_PAPERS: Paper[] = [
  {
    id: 1,
    arxiv_id: '2401.12345',
    title: 'Multi-Agent Reinforcement Learning for Autonomous Systems',
    authors: 'Galal Qassas; Ahmed Hassan',
    abstract: 'We propose a novel framework for multi-agent reinforcement learning in large-scale autonomous systems. Our approach achieves 34% improvement in coordination efficiency over state-of-the-art baselines across three benchmark environments.',
    published_date: '2024-01-15',
    ingested_at: '2025-05-12T18:30:00',
    buckets: ['autonomous_agents', 'general_ai'],
  },
  {
    id: 2,
    arxiv_id: '2402.98765',
    title: 'Foundation Models for Financial Time Series Forecasting',
    authors: 'Mei Lin; David Osei; Priya Sharma',
    abstract: 'We present FinGPT-TS, a large language model pre-trained on 15 years of intraday market data. Zero-shot transfer to new asset classes outperforms supervised LSTM baselines by 18% RMSE.',
    published_date: '2024-02-20',
    ingested_at: '2025-05-12T18:31:00',
    buckets: ['ai_finance', 'general_ai'],
  },
  {
    id: 3,
    arxiv_id: '2403.11111',
    title: 'Scalable Attention Mechanisms for Long-Context Language Models',
    authors: 'Yuki Tanaka; Maria Fernandez',
    abstract: 'We introduce SparseFlash, a sparse attention variant that reduces quadratic complexity to O(n log n) while preserving 98.7% accuracy on long-document benchmarks up to 128k tokens.',
    published_date: '2024-03-10',
    ingested_at: '2025-05-12T18:32:00',
    buckets: ['general_ai'],
  },
  {
    id: 4,
    arxiv_id: '2404.22222',
    title: 'LLM-Powered Portfolio Optimization with Sentiment Integration',
    authors: 'Carlos Reyes; Fatima Al-Rashid',
    abstract: 'This paper combines transformer-based sentiment extraction from earnings call transcripts with modern portfolio theory. Our hybrid model achieves Sharpe ratio 1.84 vs 1.21 for the market-cap baseline over a 5-year backtest.',
    published_date: '2024-04-05',
    ingested_at: '2025-05-12T18:33:00',
    buckets: ['ai_finance'],
  },
  {
    id: 5,
    arxiv_id: '2405.33333',
    title: 'Tool-Augmented Agents with Hierarchical Planning',
    authors: 'James Okafor; Li Wei; Anna Kowalski',
    abstract: 'We present HierAgent, an autonomous agent architecture that decomposes complex goals into sub-tasks via a hierarchical planner. On the AgentBench benchmark, HierAgent scores 67.4% vs 58.1% for ReAct.',
    published_date: '2024-05-22',
    ingested_at: '2025-05-12T18:34:00',
    buckets: ['autonomous_agents'],
  },
  {
    id: 6,
    arxiv_id: '2406.44444',
    title: 'Mixture-of-Experts for Efficient Large Language Model Inference',
    authors: 'Sophie Müller; Raj Patel',
    abstract: 'SparseMoE-32 activates only 2 of 32 expert sub-networks per token, reducing inference FLOPs by 6.4× with less than 1% perplexity degradation on standard NLP benchmarks.',
    published_date: '2024-06-18',
    ingested_at: '2025-05-12T18:35:00',
    buckets: ['general_ai'],
  },
  {
    id: 7,
    arxiv_id: '2407.55555',
    title: 'Deep Reinforcement Learning for Algorithmic Trading with Risk Constraints',
    authors: 'Nguyen Thanh; Elisa Romano',
    abstract: 'CVAR-DRL incorporates conditional value-at-risk as a hard constraint in the reward function. Backtesting on 10 years of equity data shows max drawdown reduced by 31% with comparable return to unconstrained agents.',
    published_date: '2024-07-11',
    ingested_at: '2025-05-12T18:36:00',
    buckets: ['ai_finance', 'autonomous_agents'],
  },
  {
    id: 8,
    arxiv_id: '2408.66666',
    title: 'Chain-of-Thought Prompting Elicits Reasoning in Large Language Models',
    authors: 'Aarav Singh; Lucia Bianchi; Tom Chen',
    abstract: 'Systematic evaluation of CoT prompting across 23 reasoning benchmarks. We find that providing step-by-step exemplars consistently improves performance by 12–41% over direct prompting, with larger gains on multi-step arithmetic tasks.',
    published_date: '2024-08-03',
    ingested_at: '2025-05-12T18:37:00',
    buckets: ['general_ai'],
  },
];

export const MOCK_PIPELINE_RUNS: PipelineRun[] = [
  {
    id: 5,
    name: 'full_pipeline',
    started_at: '2025-05-12T18:30:00',
    finished_at: '2025-05-12T18:35:22',
    duration_s: 322.45,
    status: 'success',
    paper_count: 6,
    stages: { ingested: 6, deduplicated: 0, embedded: 6, classified: 6 },
    error: null,
  },
  {
    id: 4,
    name: 'report',
    started_at: '2025-05-12T19:01:00',
    finished_at: '2025-05-12T19:03:45',
    duration_s: 164.8,
    status: 'success',
    paper_count: 8,
    stages: null,
    error: null,
  },
  {
    id: 3,
    name: 'ingest',
    started_at: '2025-05-10T14:15:00',
    finished_at: '2025-05-10T14:18:07',
    duration_s: 187.2,
    status: 'success',
    paper_count: 3,
    stages: { ingested: 3, deduplicated: 1, embedded: 3, classified: 3 },
    error: null,
  },
  {
    id: 2,
    name: 'full_pipeline',
    started_at: '2025-05-08T09:00:00',
    finished_at: '2025-05-08T09:00:45',
    duration_s: 45.3,
    status: 'error',
    paper_count: 0,
    stages: { ingested: 0 },
    error: 'Ollama connection timeout after 30s — is Ollama running?',
  },
  {
    id: 1,
    name: 'ingest',
    started_at: '2025-05-07T10:00:00',
    finished_at: '2025-05-07T10:04:22',
    duration_s: 262.1,
    status: 'success',
    paper_count: 5,
    stages: { ingested: 5, deduplicated: 0, embedded: 5, classified: 5 },
    error: null,
  },
];

export const INGESTION_CHART_DATA = [
  { month: 'Oct', general_ai: 1, autonomous_agents: 0, ai_finance: 1, total: 2 },
  { month: 'Nov', general_ai: 1, autonomous_agents: 1, ai_finance: 0, total: 2 },
  { month: 'Dec', general_ai: 2, autonomous_agents: 0, ai_finance: 1, total: 3 },
  { month: 'Jan', general_ai: 1, autonomous_agents: 1, ai_finance: 0, total: 2 },
  { month: 'Feb', general_ai: 2, autonomous_agents: 1, ai_finance: 1, total: 4 },
  { month: 'Mar', general_ai: 1, autonomous_agents: 0, ai_finance: 1, total: 2 },
  { month: 'Apr', general_ai: 3, autonomous_agents: 2, ai_finance: 1, total: 6 },
  { month: 'May', general_ai: 5, autonomous_agents: 2, ai_finance: 3, total: 8 },
];

export const BUCKET_PIE_DATA = [
  { name: 'General AI', value: 5, color: '#6366F1' },
  { name: 'Autonomous Agents', value: 2, color: '#10B981' },
  { name: 'AI × Finance', value: 3, color: '#F59E0B' },
];

export const MOCK_REPORTS: Report[] = [
  {
    id: 2,
    period: '7d',
    generated_at: '2025-05-12T19:03:45',
    paper_count: 8,
    content_html: '',
  },
  {
    id: 1,
    period: '1m',
    generated_at: '2025-05-01T10:00:00',
    paper_count: 6,
    content_html: '',
  },
];

export function generateMockReport(period: string, papers: Paper[]): string {
  const periodLabels: Record<string, string> = {
    '7d': 'Last 7 Days',
    '1m': 'Last Month',
    '3m': 'Last 3 Months',
    '6m': 'Last 6 Months',
    '1y': 'Last Year',
  };
  const label = periodLabels[period] || period;
  const date = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  const aiBucketPapers = papers.filter(p => p.buckets.includes('general_ai'));
  const agentBucketPapers = papers.filter(p => p.buckets.includes('autonomous_agents'));
  const financeBucketPapers = papers.filter(p => p.buckets.includes('ai_finance'));

  return `
<div style="font-family: system-ui, -apple-system, sans-serif; max-width: 860px; color: #1E293B; line-height: 1.7;">
  <div style="border-bottom: 2px solid #E2E8F0; padding-bottom: 1.5rem; margin-bottom: 2rem;">
    <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.5rem;">
      <div style="background:linear-gradient(135deg,#818CF8,#6366F1); width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; color:white; font-size:1.2rem;">🧬</div>
      <div>
        <h1 style="margin:0; font-size:1.5rem; font-weight:700; color:#0F172A;">Auto-Researcher Digest</h1>
        <p style="margin:0; color:#64748B; font-size:0.9rem;">${label} · Generated ${date} · ${papers.length} papers analysed</p>
      </div>
    </div>
  </div>

  <div style="background:#F8FAFC; border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:2rem; border-left:4px solid #6366F1;">
    <h2 style="margin:0 0 0.6rem; font-size:1rem; font-weight:600; color:#6366F1; text-transform:uppercase; letter-spacing:0.05em;">Executive Summary</h2>
    <p style="margin:0; color:#475569;">
      Over the selected period, ${papers.length} papers were ingested and classified across three research domains.
      The dominant theme is the maturation of <strong>large language model architectures</strong> — from efficient attention mechanisms to mixture-of-experts routing — alongside growing application of AI to autonomous decision-making and financial markets.
      Cross-domain signals show a convergence of agent frameworks and deep RL toward structured financial environments.
    </p>
  </div>

  <!-- General AI Section -->
  <div style="margin-bottom:2rem;">
    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:1rem;">
      <div style="background:linear-gradient(135deg,#818CF8,#6366F1); width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1rem;">🧠</div>
      <h2 style="margin:0; font-size:1.15rem; font-weight:700; color:#0F172A;">General AI</h2>
      <span style="background:#EEF2FF; color:#6366F1; padding:2px 10px; border-radius:999px; font-size:0.8rem; font-weight:600;">${aiBucketPapers.length} papers</span>
    </div>
    <div style="background:#FAFAFA; border:1px solid #E2E8F0; border-radius:10px; padding:1rem 1.25rem; margin-bottom:1rem;">
      <p style="margin:0; color:#475569; font-size:0.95rem;">
        <strong>Key Themes:</strong> The General AI bucket this period is dominated by architectural innovations in transformer-based models. SparseFlash's O(n log n) attention and SparseMoE-32's expert routing both address the fundamental compute bottleneck at scale. Chain-of-thought prompting research confirms that reasoning improvements are emergent rather than trained — a critical insight for evaluation methodology.
      </p>
    </div>
    ${aiBucketPapers.map(p => `
    <div style="border:1px solid #E2E8F0; border-radius:8px; padding:0.875rem 1rem; margin-bottom:0.6rem; background:white;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:1rem;">
        <div style="flex:1;">
          <p style="margin:0 0 0.25rem; font-weight:600; color:#0F172A; font-size:0.95rem;">${p.title}</p>
          <p style="margin:0 0 0.4rem; color:#94A3B8; font-size:0.82rem;">${p.authors} · ${p.published_date} · arXiv:${p.arxiv_id}</p>
          <p style="margin:0; color:#64748B; font-size:0.875rem;">${p.abstract.slice(0, 180)}…</p>
        </div>
      </div>
    </div>`).join('')}
  </div>

  <!-- Autonomous Agents Section -->
  <div style="margin-bottom:2rem;">
    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:1rem;">
      <div style="background:linear-gradient(135deg,#34D399,#059669); width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1rem;">🤖</div>
      <h2 style="margin:0; font-size:1.15rem; font-weight:700; color:#0F172A;">Autonomous Agents</h2>
      <span style="background:#ECFDF5; color:#10B981; padding:2px 10px; border-radius:999px; font-size:0.8rem; font-weight:600;">${agentBucketPapers.length} papers</span>
    </div>
    <div style="background:#FAFAFA; border:1px solid #E2E8F0; border-radius:10px; padding:1rem 1.25rem; margin-bottom:1rem;">
      <p style="margin:0; color:#475569; font-size:0.95rem;">
        <strong>Key Themes:</strong> Hierarchical planning and multi-agent coordination are the central advances this period. HierAgent's sub-task decomposition shows that structured planning outperforms reactive ReAct-style agents on complex, multi-step tasks. The multi-agent RL work highlights that coordination gains compound as system scale increases.
      </p>
    </div>
    ${agentBucketPapers.map(p => `
    <div style="border:1px solid #E2E8F0; border-radius:8px; padding:0.875rem 1rem; margin-bottom:0.6rem; background:white;">
      <p style="margin:0 0 0.25rem; font-weight:600; color:#0F172A; font-size:0.95rem;">${p.title}</p>
      <p style="margin:0 0 0.4rem; color:#94A3B8; font-size:0.82rem;">${p.authors} · ${p.published_date} · arXiv:${p.arxiv_id}</p>
      <p style="margin:0; color:#64748B; font-size:0.875rem;">${p.abstract.slice(0, 180)}…</p>
    </div>`).join('')}
  </div>

  <!-- AI Finance Section -->
  <div style="margin-bottom:2rem;">
    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:1rem;">
      <div style="background:linear-gradient(135deg,#FCD34D,#D97706); width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1rem;">📈</div>
      <h2 style="margin:0; font-size:1.15rem; font-weight:700; color:#0F172A;">AI × Finance</h2>
      <span style="background:#FFFBEB; color:#D97706; padding:2px 10px; border-radius:999px; font-size:0.8rem; font-weight:600;">${financeBucketPapers.length} papers</span>
    </div>
    <div style="background:#FAFAFA; border:1px solid #E2E8F0; border-radius:10px; padding:1rem 1.25rem; margin-bottom:1rem;">
      <p style="margin:0; color:#475569; font-size:0.95rem;">
        <strong>Key Themes:</strong> Three distinct AI-finance applications emerge: foundation models for price forecasting, LLM-driven sentiment integration for portfolio construction, and risk-constrained RL for algorithmic trading. The common thread is incorporating unstructured language signals into traditionally quantitative frameworks — with consistent alpha generation in backtests.
      </p>
    </div>
    ${financeBucketPapers.map(p => `
    <div style="border:1px solid #E2E8F0; border-radius:8px; padding:0.875rem 1rem; margin-bottom:0.6rem; background:white;">
      <p style="margin:0 0 0.25rem; font-weight:600; color:#0F172A; font-size:0.95rem;">${p.title}</p>
      <p style="margin:0 0 0.4rem; color:#94A3B8; font-size:0.82rem;">${p.authors} · ${p.published_date} · arXiv:${p.arxiv_id}</p>
      <p style="margin:0; color:#64748B; font-size:0.875rem;">${p.abstract.slice(0, 180)}…</p>
    </div>`).join('')}
  </div>

  <!-- Cross-Domain Synthesis -->
  <div style="background:linear-gradient(135deg,#EEF2FF,#ECFDF5); border-radius:12px; padding:1.25rem 1.5rem; border:1px solid #E2E8F0;">
    <h2 style="margin:0 0 0.6rem; font-size:1rem; font-weight:600; color:#0F172A;">🔗 Cross-Domain Synthesis</h2>
    <p style="margin:0; color:#475569;">
      A convergence pattern is visible across all three buckets: <strong>general AI capabilities (efficient transformers, CoT reasoning) are being systematically applied to agentic and financial domains</strong>.
      The most promising cross-domain signal is RL-based agents with risk constraints entering financial environments — combining the coordination advances from multi-agent RL with the drawdown-control imperatives of institutional trading.
      Expect the 3m and 6m windows to show significantly more papers at this intersection as the research community catches up to FinGPT-TS's zero-shot transfer results.
    </p>
  </div>
</div>
  `.trim();
}
