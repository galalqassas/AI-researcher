import { useState, useEffect } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import {
  Brain, Bot, TrendingUp, Database, FileText, Activity,
  CheckCircle, XCircle, Clock, ArrowUpRight, Zap, RefreshCw,
  AlertCircle,
} from 'lucide-react';
import {
  fetchPapers, fetchPaperStats, fetchPipelineRuns, fetchReports,
  BUCKET_CONFIG, type BucketKey, type PipelineRun, type PaperStats,
} from '../data/api';

function Icon3D({ children, gradientFrom, gradientTo, shadowColor }: {
  children: React.ReactNode; gradientFrom: string; gradientTo: string; shadowColor: string;
}) {
  return (
    <div
      className="w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0"
      style={{
        background: `linear-gradient(145deg, ${gradientFrom}, ${gradientTo})`,
        boxShadow: `0 8px 20px ${shadowColor}40, inset 0 1px 1px rgba(255,255,255,0.35), inset 0 -1px 1px rgba(0,0,0,0.12)`,
      }}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, gradientFrom, gradientTo, shadowColor, icon, trend }: {
  label: string; value: string | number; sub?: string;
  gradientFrom: string; gradientTo: string; shadowColor: string;
  icon: React.ReactNode; trend?: { value: string; up: boolean };
}) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-[#E2E8F0] hover:shadow-md transition-all duration-200 group">
      <div className="flex items-start justify-between mb-4">
        <Icon3D gradientFrom={gradientFrom} gradientTo={gradientTo} shadowColor={shadowColor}>{icon}</Icon3D>
        {trend && (
          <span className="flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs"
            style={{ background: trend.up ? '#ECFDF5' : '#FEF2F2', color: trend.up ? '#059669' : '#DC2626' }}>
            <ArrowUpRight size={11} style={{ transform: trend.up ? 'none' : 'rotate(90deg)' }} />
            {trend.value}
          </span>
        )}
      </div>
      <p className="text-[#64748B] text-sm mb-0.5">{label}</p>
      <p className="text-[#0F172A] text-3xl" style={{ fontWeight: 700 }}>{value}</p>
      {sub && <p className="text-[#94A3B8] text-xs mt-1">{sub}</p>}
    </div>
  );
}

const CUSTOM_TOOLTIP_STYLE = {
  background: 'white', border: '1px solid #E2E8F0', borderRadius: '10px',
  boxShadow: '0 4px 16px rgba(0,0,0,0.08)', padding: '10px 14px', fontSize: '0.825rem',
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={CUSTOM_TOOLTIP_STYLE}>
      <p className="text-[#0F172A] mb-1" style={{ fontWeight: 600 }}>{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} style={{ color: entry.color, margin: '2px 0' }}>
          {entry.name}: <strong>{entry.value}</strong>
        </p>
      ))}
    </div>
  );
}

const PieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, name, value }: any) => {
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight={700}>
      {value}
    </text>
  );
};

const RUN_ICON: Record<string, React.ReactNode> = {
  success: <CheckCircle size={14} className="text-emerald-500" />,
  error: <XCircle size={14} className="text-rose-500" />,
  running: <RefreshCw size={14} className="text-blue-500 animate-spin" />,
};

const STATUS_PILL: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-700',
  error: 'bg-rose-50 text-rose-700',
  running: 'bg-blue-50 text-blue-700',
};

function fmtDuration(s: number | null) {
  if (s == null) return '—';
  if (s < 60) return `${s.toFixed(0)}s`;
  return `${(s / 60).toFixed(1)}m`;
}

function fmtTime(dt: string) {
  return new Date(dt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

interface DashboardHomeProps {
  onPapersLoaded?: (count: number) => void;
}

export function DashboardHome({ onPapersLoaded }: DashboardHomeProps) {
  const [stats, setStats] = useState<PaperStats | null>(null);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [reportCount, setReportCount] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchPaperStats(), fetchPipelineRuns(4), fetchReports()])
      .then(([s, r, reports]) => {
        setStats(s);
        setRuns(r);
        setReportCount(reports.length);
        if (onPapersLoaded) onPapersLoaded(s.total);
      })
      .catch(e => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-start gap-3 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
          <AlertCircle size={16} className="text-rose-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-rose-700 text-sm" style={{ fontWeight: 600 }}>Failed to load dashboard data</p>
            <p className="text-rose-600 text-xs mt-0.5">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return <div className="p-6 text-center text-[#94A3B8]">Loading dashboard…</div>;
  }

  const totalPapers = stats.total;
  const recentRuns = runs.slice(0, 4);
  const lastRun = runs[0];
  const successRate = runs.length ? Math.round((runs.filter(r => r.status === 'success').length / runs.length) * 100) : 0;

  // Build chart data from stats — daily granularity
  const chartData = stats.per_date.map(d => {
    const dt = new Date(d.date + 'T00:00:00');
    const label = dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    return {
      date: label,
      general_ai: d.general_ai || 0,
      autonomous_agents: d.autonomous_agents || 0,
      ai_finance: d.ai_finance || 0,
      total: d.count,
    };
  });

  const pieData = (Object.entries(stats.per_bucket) as [string, number][]).map(([key, val]) => ({
    name: BUCKET_CONFIG[key as BucketKey]?.label ?? key,
    value: val,
    color: BUCKET_CONFIG[key as BucketKey]?.color ?? '#94A3B8',
  }));

  const papersToday = stats.today;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[#0F172A]" style={{ fontWeight: 700 }}>Dashboard</h1>
        <p className="text-[#64748B] text-sm mt-0.5">Real-time overview of your Auto-Researcher pipeline</p>
      </div>

      {lastRun?.status === 'error' && (
        <div className="flex items-start gap-3 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
          <AlertCircle size={16} className="text-rose-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-rose-700 text-sm" style={{ fontWeight: 600 }}>Last pipeline run failed</p>
            <p className="text-rose-600 text-xs mt-0.5">{lastRun.error}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Total Papers" value={totalPapers} sub="across 3 research buckets"
          gradientFrom="#818CF8" gradientTo="#6366F1" shadowColor="#6366F1"
          icon={<Database size={20} color="white" />} />
        <StatCard label="Papers Today" value={papersToday} sub="ingested today"
          gradientFrom="#34D399" gradientTo="#059669" shadowColor="#10B981"
          icon={<Zap size={20} color="white" />} />
        <StatCard label="Reports" value={reportCount} sub="generated"
          gradientFrom="#FCD34D" gradientTo="#D97706" shadowColor="#F59E0B"
          icon={<FileText size={20} color="white" />} />
        <StatCard label="Pipeline Success" value={`${successRate}%`}
          sub={`of ${runs.length} recent runs`}
          gradientFrom="#FB7185" gradientTo="#E11D48" shadowColor="#F43F5E"
          icon={<Activity size={20} color="white" />}
          trend={runs.length > 0 ? { value: `${runs.filter(r => r.status === 'error').length} failures`, up: runs.filter(r => r.status === 'error').length === 0 } : undefined} />
      </div>

      {/* Bucket Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(Object.entries(BUCKET_CONFIG) as [string, typeof BUCKET_CONFIG[keyof typeof BUCKET_CONFIG]][]).map(([key, cfg]) => {
          const count = stats.per_bucket[key] || 0;
          const pct = totalPapers ? Math.round((count / totalPapers) * 100) : 0;
          return (
            <div key={key} className="rounded-2xl p-5 border relative overflow-hidden"
              style={{ background: cfg.colorLight, borderColor: cfg.color + '30' }}>
              <div className="absolute top-0 right-0 w-24 h-24 rounded-full opacity-10 -translate-y-8 translate-x-8"
                style={{ background: cfg.color }} />
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                  style={{ background: `linear-gradient(145deg, ${cfg.gradientFrom}, ${cfg.gradientTo})`, boxShadow: `0 4px 12px ${cfg.color}40` }}>
                  {key === 'general_ai' ? '🧠' : key === 'autonomous_agents' ? '🤖' : '📈'}
                </div>
                <div>
                  <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{cfg.label}</p>
                  <p className="text-xs" style={{ color: cfg.color }}>{cfg.categories.join(', ')}</p>
                </div>
              </div>
              <div className="flex items-end justify-between">
                <p className="text-4xl" style={{ fontWeight: 700, color: cfg.color }}>{count}</p>
                <p className="text-sm" style={{ color: cfg.color, fontWeight: 600 }}>{pct}%</p>
              </div>
              <div className="mt-3 h-1.5 rounded-full bg-white/60">
                <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: cfg.color }} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-white rounded-2xl border border-[#E2E8F0] p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-[#0F172A]" style={{ fontWeight: 600 }}>Papers Ingested Over Time</h3>
              <p className="text-[#94A3B8] text-xs mt-1">Daily breakdown by research bucket</p>
            </div>
            <div className="flex items-center gap-3">
              {Object.entries(BUCKET_CONFIG).map(([key, cfg]) => (
                <div key={key} className="flex items-center gap-1">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: cfg.color }} />
                  <span className="text-[#64748B] text-xs">{cfg.label.split(' ')[0]}</span>
                </div>
              ))}
            </div>
          </div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradAI" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#6366F1" stopOpacity={0.325} /><stop offset="95%" stopColor="#6366F1" stopOpacity={0.025} /></linearGradient>
                  <linearGradient id="gradAgents" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10B981" stopOpacity={0.325} /><stop offset="95%" stopColor="#10B981" stopOpacity={0.025} /></linearGradient>
                  <linearGradient id="gradFinance" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#F59E0B" stopOpacity={0.325} /><stop offset="95%" stopColor="#F59E0B" stopOpacity={0.025} /></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="general_ai" name="General AI" stroke="#6366F1" strokeWidth={2.75} fill="url(#gradAI)" />
                <Area type="monotone" dataKey="autonomous_agents" name="Autonomous Agents" stroke="#10B981" strokeWidth={2.75} fill="url(#gradAgents)" />
                <Area type="monotone" dataKey="ai_finance" name="AI Finance" stroke="#F59E0B" strokeWidth={2.75} fill="url(#gradFinance)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-[#94A3B8] text-sm">No ingestion data yet</div>
          )}
        </div>

        {/* Donut chart */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5">
          <div className="mb-4">
            <h3 className="text-[#0F172A]" style={{ fontWeight: 600 }}>Bucket Distribution</h3>
            <p className="text-[#94A3B8] text-xs mt-0.5">Share of {totalPapers} total papers</p>
          </div>
          {pieData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={170}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={48} outerRadius={78} paddingAngle={3} dataKey="value" labelLine={false} label={PieLabel}>
                    {pieData.map((entry) => <Cell key={entry.name} fill={entry.color} />)}
                  </Pie>
                  <Tooltip formatter={(v: number, name: string) => [`${v} papers`, name]} contentStyle={CUSTOM_TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 mt-1">
                {pieData.map(d => (
                  <div key={d.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-sm" style={{ background: d.color }} /><span className="text-[#475569] text-xs">{d.name}</span></div>
                    <span className="text-[#0F172A] text-xs" style={{ fontWeight: 700 }}>{d.value} <span className="text-[#94A3B8]">({totalPapers ? Math.round((d.value / totalPapers) * 100) : 0}%)</span></span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-[#94A3B8] text-sm">No papers yet</div>
          )}
        </div>
      </div>

      {/* Recent Papers + Pipeline Runs */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {/* Recent Papers */}
        <RecentPapersCard />
        {/* Pipeline runs */}
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[#0F172A]" style={{ fontWeight: 600 }}>Pipeline Runs</h3>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[#64748B] text-xs">Monitoring active</span>
            </div>
          </div>
          <div className="space-y-2">
            {recentRuns.length === 0 && <p className="text-[#94A3B8] text-sm py-4 text-center">No pipeline runs yet</p>}
            {recentRuns.map(run => (
              <div key={run.id} className="flex items-center gap-3 p-3 rounded-xl border border-[#F1F5F9] hover:bg-[#F8FAFC] transition-colors">
                <div className="flex items-center gap-1.5 w-24 flex-shrink-0">
                  {RUN_ICON[run.status]}
                  <span className={`text-xs px-1.5 py-0.5 rounded-md ${STATUS_PILL[run.status]}`} style={{ fontWeight: 600 }}>{run.status}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[#0F172A] text-sm" style={{ fontWeight: 500 }}>{run.name.replace(/_/g, ' ')}</p>
                  <p className="text-[#94A3B8] text-xs">{fmtTime(run.started_at)}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="flex items-center gap-1 text-[#64748B] text-xs"><Clock size={10} />{fmtDuration(run.duration_s)}</div>
                  {run.paper_count != null && run.paper_count > 0 && <p className="text-[#94A3B8] text-xs">{run.paper_count} papers</p>}
                </div>
              </div>
            ))}
          </div>
          {lastRun?.stages && lastRun.status === 'success' && Object.values(lastRun.stages).some(v => typeof v === 'number') && (
            <div className="mt-4 p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <p className="text-[#64748B] text-xs mb-2" style={{ fontWeight: 600 }}>Last run stages</p>
              <div className="grid grid-cols-4 gap-2">
                {Object.entries(lastRun.stages)
                  .filter(([, count]) => typeof count === 'number')
                  .map(([stage, count]) => (
                    <div key={stage} className="text-center">
                      <p className="text-[#0F172A] text-base" style={{ fontWeight: 700 }}>{count}</p>
                      <p className="text-[#94A3B8]" style={{ fontSize: '0.68rem' }}>{stage}</p>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RecentPapersCard() {
  const [papers, setPapers] = useState<any[]>([]);
  useEffect(() => { fetchPapers(undefined, 1, 5).then(d => setPapers(d.results)).catch(() => {}); }, []);
  return (
    <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[#0F172A]" style={{ fontWeight: 600 }}>Recent Papers</h3>
      </div>
      <div className="space-y-3">
        {papers.length === 0 && <p className="text-[#94A3B8] text-sm py-4 text-center">No papers yet</p>}
        {papers.map(paper => (
          <div key={paper.id} className="flex items-start gap-3 group">
            <div className="flex gap-1 flex-wrap pt-0.5">
              {(paper.buckets || []).map((b: string) => (
                <span key={b} className="inline-block w-1.5 h-1.5 rounded-full mt-1.5"
                  style={{ background: BUCKET_CONFIG[b as BucketKey]?.color ?? '#94A3B8' }} />
              ))}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[#0F172A] text-sm truncate" style={{ fontWeight: 500 }}>{paper.title}</p>
              <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                <span className="text-[#94A3B8] text-xs">arXiv:{paper.arxiv_id}</span>
                <span className="text-[#CBD5E1]">·</span>
                <span className="text-[#94A3B8] text-xs">{paper.published_date}</span>
                {(paper.buckets || []).map((b: string) => (
                  <span key={b} className="text-xs px-1.5 py-0.5 rounded-md"
                    style={{ background: BUCKET_CONFIG[b as BucketKey]?.colorLight ?? '#F1F5F9', color: BUCKET_CONFIG[b as BucketKey]?.color ?? '#64748B', fontWeight: 600, fontSize: '0.7rem' }}>
                    {BUCKET_CONFIG[b as BucketKey]?.label ?? b}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}