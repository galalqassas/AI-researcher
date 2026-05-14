import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import {
  CheckCircle, XCircle, RefreshCw, Clock, ChevronDown, ChevronUp, Play,
  Database, AlertTriangle, Loader2,
} from 'lucide-react';
import { fetchPipelineRuns, runPipeline, type PipelineRun } from '../data/api';
import { usePollingEffect, getAdaptiveInterval } from '../hooks/usePolling';

function fmtDuration(s: number | null) {
  if (s == null) return '—';
  if (s < 60) return `${s.toFixed(0)}s`;
  return `${(s / 60).toFixed(1)}m`;
}
function fmtTime(dt: string) {
  return new Date(dt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  success: <CheckCircle size={15} className="text-emerald-500" />,
  error: <XCircle size={15} className="text-rose-500" />,
  running: <RefreshCw size={15} className="text-blue-500 animate-spin" />,
};

const STATUS_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  success: { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' },
  error: { bg: '#FFF1F2', text: '#E11D48', border: '#FECDD3' },
  running: { bg: '#EFF6FF', text: '#2563EB', border: '#BFDBFE' },
};

const STAGE_COLORS = ['#6366F1', '#10B981', '#F59E0B', '#8B5CF6'];

function ExpandableRun({ run }: { run: PipelineRun }) {
  const [expanded, setExpanded] = useState(false);
  const s = STATUS_STYLE[run.status] || STATUS_STYLE.success;

  return (
    <div className="rounded-2xl border overflow-hidden transition-all duration-200" style={{ borderColor: s.border, background: 'white' }}>
      <button className="w-full flex items-center gap-4 p-4 hover:bg-[#F8FAFC] transition-colors text-left" onClick={() => setExpanded(!expanded)}>
        <div className="flex-shrink-0">{STATUS_ICON[run.status]}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{run.name.replace(/_/g, ' ')}</p>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: s.bg, color: s.text, fontWeight: 600, border: `1px solid ${s.border}` }}>{run.status}</span>
          </div>
          <p className="text-[#94A3B8] text-xs mt-0.5">{fmtTime(run.started_at)}</p>
        </div>
        <div className="flex items-center gap-6 flex-shrink-0">
          <div className="text-right">
            <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{fmtDuration(run.duration_s)}</p>
            <p className="text-[#94A3B8] text-xs">duration</p>
          </div>
          {run.paper_count != null && run.paper_count > 0 && (
            <div className="text-right"><p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{run.paper_count}</p><p className="text-[#94A3B8] text-xs">papers</p></div>
          )}
          {expanded ? <ChevronUp size={14} className="text-[#94A3B8]" /> : <ChevronDown size={14} className="text-[#94A3B8]" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-[#F1F5F9]">
          {run.stages && (
            <div className="mt-3">
              <p className="text-[#64748B] text-xs mb-2" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Stage Breakdown</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Object.entries(run.stages).map(([stage, count], i) => (
                  <div key={stage} className="rounded-xl p-3 text-center"
                    style={{ background: STAGE_COLORS[i % STAGE_COLORS.length] + '10', border: `1px solid ${STAGE_COLORS[i % STAGE_COLORS.length]}25` }}>
                    <p className="text-lg" style={{ fontWeight: 700, color: STAGE_COLORS[i % STAGE_COLORS.length] }}>{count}</p>
                    <p className="text-xs text-[#64748B] mt-0.5 capitalize">{stage}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {run.error && (
            <div className="mt-3 flex items-start gap-2 bg-rose-50 border border-rose-200 rounded-xl p-3">
              <AlertTriangle size={14} className="text-rose-500 mt-0.5 flex-shrink-0" />
              <div><p className="text-rose-700 text-xs" style={{ fontWeight: 600 }}>Error Details</p><p className="text-rose-600 text-xs mt-0.5 font-mono">{run.error}</p></div>
            </div>
          )}
          <div className="mt-3 flex items-center gap-4 text-xs text-[#94A3B8]">
            <span>Run #{run.id}</span>
            {run.finished_at && <span>Finished: {fmtTime(run.finished_at)}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export function PipelinePanel() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const refresh = () => {
    fetchPipelineRuns(20).then(setRuns).catch(e => setError(e.message)).finally(() => setLoading(false));
  };

  const silentRefresh = () => {
    fetchPipelineRuns(20).then(data => { setRuns(data); setError(null); }).catch(() => {});
  };

  useEffect(() => { refresh(); }, []);
  usePollingEffect(silentRefresh, getAdaptiveInterval(runs), [runs.length]);

  const handleRunPipeline = async () => {
    setRunning(true);
    try {
      await runPipeline();
    } catch (e: any) {
      // Pipeline might take a while, that's ok
    }
    // Wait a moment then refresh
    setTimeout(() => { refresh(); setRunning(false); }, 2000);
  };

  const successRuns = runs.filter(r => r.status === 'success');
  const ingestRuns = successRuns.filter(r => r.name === 'ingest' || r.name === 'full_pipeline');
  const totalPapers = ingestRuns.reduce((s, r) => s + (r.paper_count ?? 0), 0);
  const avgDuration = successRuns.reduce((s, r) => s + (r.duration_s ?? 0), 0) / (successRuns.length || 1);
  const successRate = runs.length ? Math.round((successRuns.length / runs.length) * 100) : 0;
  const lastSuccess = successRuns[0];

  const chartData = runs.filter(r => r.duration_s).map(r => ({
    name: fmtTime(r.started_at), duration: parseFloat((r.duration_s! / 60).toFixed(2)), status: r.status, id: r.id,
  })).reverse();

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-[#0F172A]" style={{ fontWeight: 700 }}>Pipeline & Operations</h1>
          <p className="text-[#64748B] text-sm mt-0.5">Run history, stage metrics, and system status</p>
        </div>
        <button onClick={handleRunPipeline} disabled={running}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm transition-all disabled:opacity-60"
          style={{ background: 'linear-gradient(145deg, #818CF8, #6366F1)', color: 'white', fontWeight: 600, boxShadow: '0 4px 12px #6366F140' }}>
          {running ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {running ? 'Running…' : 'Run Pipeline'}
        </button>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          { label: 'Success Rate', value: `${successRate}%`, sub: `${successRuns.length}/${runs.length} runs`, icon: <CheckCircle size={20} color="white" />, from: '#34D399', to: '#059669', shadow: '#10B981' },
          { label: 'Avg Duration', value: fmtDuration(avgDuration), sub: 'across successful runs', icon: <Clock size={20} color="white" />, from: '#818CF8', to: '#6366F1', shadow: '#6366F1' },
          { label: 'Total Papers', value: totalPapers, sub: 'ingested across all runs', icon: <Database size={20} color="white" />, from: '#FCD34D', to: '#D97706', shadow: '#F59E0B' },
          { label: 'Last Run', value: lastSuccess ? fmtTime(lastSuccess.started_at) : '—', sub: lastSuccess ? `${fmtDuration(lastSuccess.duration_s)} · ${lastSuccess.paper_count} papers` : '', icon: <RefreshCw size={20} color="white" />, from: '#A78BFA', to: '#7C3AED', shadow: '#8B5CF6' },
        ].map(m => (
          <div key={m.label} className="bg-white rounded-2xl border border-[#E2E8F0] p-5">
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center mb-3"
              style={{ background: `linear-gradient(145deg, ${m.from}, ${m.to})`, boxShadow: `0 6px 16px ${m.shadow}40, inset 0 1px 1px rgba(255,255,255,0.35)` }}>
              {m.icon}
            </div>
            <p className="text-[#64748B] text-sm">{m.label}</p>
            <p className="text-[#0F172A] text-2xl mt-0.5" style={{ fontWeight: 700 }}>{m.value}</p>
            <p className="text-[#94A3B8] text-xs mt-0.5">{m.sub}</p>
          </div>
        ))}
      </div>

      {chartData.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5">
          <div className="mb-4">
            <h3 className="text-[#0F172A]" style={{ fontWeight: 600 }}>Run Duration History</h3>
            <p className="text-[#94A3B8] text-xs mt-0.5">Minutes per pipeline run (chronological)</p>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} unit="m" />
              <Tooltip formatter={(v: number) => [`${v}m`, 'Duration']} contentStyle={{ background: 'white', border: '1px solid #E2E8F0', borderRadius: '10px', boxShadow: '0 4px 16px rgba(0,0,0,0.08)', padding: '10px 14px', fontSize: '0.825rem' }} />
              <Bar dataKey="duration" radius={[6, 6, 0, 0]}>
                {chartData.map((entry, i) => <Cell key={i} fill={entry.status === 'success' ? '#6366F1' : entry.status === 'error' ? '#F43F5E' : '#60A5FA'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div>
        <h3 className="text-[#475569] text-sm mb-3" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Run History</h3>
        {loading ? (
          <div className="flex items-center justify-center py-8"><Loader2 className="animate-spin text-[#6366F1]" size={24} /></div>
        ) : error ? (
          <p className="text-[#94A3B8] text-sm text-center py-4">Error: {error}</p>
        ) : runs.length === 0 ? (
          <p className="text-[#94A3B8] text-sm text-center py-4">No pipeline runs yet</p>
        ) : (
          <div className="space-y-2">{runs.map(run => <ExpandableRun key={run.id} run={run} />)}</div>
        )}
      </div>
    </div>
  );
}

export default PipelinePanel;