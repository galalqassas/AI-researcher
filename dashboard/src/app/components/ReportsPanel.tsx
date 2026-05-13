import { useState, useEffect } from 'react';
import { FileText, Loader2, Clock, CheckCircle, ChevronRight, X, Download, Sparkles, AlertCircle } from 'lucide-react';
import { fetchReports, fetchReport, generateReport, type Report } from '../data/api';

const PERIODS = [
  { key: '7d', label: 'Last 7 Days', sub: 'Quick weekly digest' },
  { key: '1m', label: 'Last Month', sub: '~30 days of papers' },
  { key: '3m', label: 'Last 3 Months', sub: 'Quarterly overview' },
  { key: '6m', label: 'Last 6 Months', sub: 'Half-year synthesis' },
  { key: '1y', label: 'Last Year', sub: 'Annual landscape' },
];

const PERIOD_COLORS: Record<string, { from: string; to: string; shadow: string; light: string; text: string }> = {
  '7d': { from: '#818CF8', to: '#6366F1', shadow: '#6366F1', light: '#EEF2FF', text: '#6366F1' },
  '1m': { from: '#34D399', to: '#059669', shadow: '#10B981', light: '#ECFDF5', text: '#059669' },
  '3m': { from: '#FCD34D', to: '#D97706', shadow: '#F59E0B', light: '#FFFBEB', text: '#D97706' },
  '6m': { from: '#FB7185', to: '#E11D48', shadow: '#F43F5E', light: '#FFF1F2', text: '#E11D48' },
  '1y': { from: '#A78BFA', to: '#7C3AED', shadow: '#8B5CF6', light: '#F5F3FF', text: '#7C3AED' },
};

const STAGE_MESSAGES: Record<number, string> = {
  0: 'Querying arXiv for papers…',
  1: 'Running hybrid classification (RRF + cosine)…',
  2: 'Generating per-paper summaries (light model)…',
  3: 'Synthesising bucket themes (heavy model)…',
  4: 'Building cross-domain analysis…',
};

function fmtTime(dt: string) {
  return new Date(dt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function ReportsPanel() {
  const [generating, setGenerating] = useState<string | null>(null);
  const [stage, setStage] = useState(0);
  const [viewingReport, setViewingReport] = useState<Report | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingError, setGeneratingError] = useState<string | null>(null);

  useEffect(() => {
    fetchReports().then(setReports).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, []);

  async function handleGenerate(period: string) {
    setGenerating(period);
    setStage(0);
    setGeneratingError(null);
    // Show progress stages while waiting
    const interval = setInterval(() => setStage(s => Math.min(s + 1, 4)), 1500);
    try {
      const result = await generateReport(period);
      // Refresh reports list
      const updated = await fetchReports();
      setReports(updated);
      // Fetch the full report content
      const fullReport = await fetchReport(result.id);
      setViewingReport(fullReport);
    } catch (e: any) {
      setGeneratingError(e.message || 'Generation failed');
    } finally {
      clearInterval(interval);
      setGenerating(null);
      setStage(0);
    }
  }

  const periodColors = (p: string) => PERIOD_COLORS[p] || PERIOD_COLORS['7d'];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[#0F172A]" style={{ fontWeight: 700 }}>Research Reports</h1>
        <p className="text-[#64748B] text-sm mt-0.5">Generate LLM-powered digests grouped by research bucket with cross-domain synthesis</p>
      </div>

      {generatingError && (
        <div className="flex items-start gap-3 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
          <AlertCircle size={16} className="text-rose-500 mt-0.5 flex-shrink-0" />
          <div><p className="text-rose-700 text-sm" style={{ fontWeight: 600 }}>Generation failed</p><p className="text-rose-600 text-xs mt-0.5">{generatingError}</p></div>
        </div>
      )}

      <div>
        <h3 className="text-[#475569] text-sm mb-3" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Generate New Report</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
          {PERIODS.map(({ key, label, sub }) => {
            const isGenerating = generating === key;
            const c = periodColors(key);
            const existingReport = reports.find(r => r.period === key);
            return (
              <button key={key} onClick={() => !generating && handleGenerate(key)} disabled={!!generating}
                className="group relative flex flex-col items-start p-4 rounded-2xl border text-left transition-all duration-200 hover:shadow-md focus:outline-none"
                style={{ background: isGenerating ? c.light : 'white', borderColor: isGenerating ? c.text + '50' : '#E2E8F0', opacity: generating && !isGenerating ? 0.5 : 1, cursor: generating ? 'not-allowed' : 'pointer' }}>
                <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3 flex-shrink-0"
                  style={{ background: `linear-gradient(145deg, ${c.from}, ${c.to})`, boxShadow: `0 4px 12px ${c.shadow}40` }}>
                  {isGenerating ? <Loader2 size={16} color="white" className="animate-spin" /> : <Sparkles size={16} color="white" />}
                </div>
                <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{label}</p>
                <p className="text-[#94A3B8] text-xs mt-0.5">{sub}</p>
                {isGenerating && (
                  <div className="mt-3 w-full">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Loader2 size={10} style={{ color: c.text }} className="animate-spin" />
                      <span className="text-xs" style={{ color: c.text }}>{STAGE_MESSAGES[stage]}</span>
                    </div>
                    <div className="h-1 rounded-full bg-gray-100 overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${((stage + 1) / 5) * 100}%`, background: `linear-gradient(90deg, ${c.from}, ${c.to})` }} />
                    </div>
                    <p className="text-right text-xs mt-1" style={{ color: c.text }}>Stage {stage + 1} / 5</p>
                  </div>
                )}
                {!isGenerating && existingReport && (
                  <p className="mt-2 text-xs" style={{ color: c.text }}>Last: {fmtTime(existingReport.generated_at)}</p>
                )}
                {!isGenerating && <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: c.text }}><ChevronRight size={14} /></div>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-start gap-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-3">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'linear-gradient(145deg, #818CF8, #6366F1)' }}>
          <span className="text-white text-xs">💡</span>
        </div>
        <div>
          <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>Cost-aware generation</p>
          <p className="text-[#64748B] text-xs mt-0.5">
            Per-paper summaries use the light model. Bucket synthesis and cross-domain analysis use the heavy model. LLM responses are cached via SHA-256 key — repeat runs for the same papers are free.
          </p>
        </div>
      </div>

      <div>
        <h3 className="text-[#475569] text-sm mb-3" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Report History</h3>
        {loading ? (
          <div className="flex items-center justify-center py-8"><Loader2 className="animate-spin text-[#6366F1]" size={24} /></div>
        ) : reports.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[#E2E8F0] p-8 text-center">
            <FileText size={32} className="text-[#CBD5E1] mx-auto mb-2" />
            <p className="text-[#94A3B8]">No reports yet — generate one above</p>
          </div>
        ) : (
          <div className="space-y-2">
            {reports.map(report => {
              const c = periodColors(report.period);
              const periodLabel = PERIODS.find(p => p.key === report.period)?.label ?? report.period;
              return (
                <div key={report.id}
                  className="bg-white rounded-2xl border border-[#E2E8F0] p-4 flex items-center gap-4 hover:shadow-sm transition-all cursor-pointer"
                  onClick={() => { setViewingReport(report); }}>
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: `linear-gradient(145deg, ${c.from}, ${c.to})`, boxShadow: `0 4px 12px ${c.shadow}30` }}>
                    <FileText size={16} color="white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{periodLabel} Report</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="flex items-center gap-1 text-xs text-[#94A3B8]"><Clock size={10} />{fmtTime(report.generated_at)}</span>
                      <span className="flex items-center gap-1 text-xs text-[#94A3B8]"><FileText size={10} />{report.paper_count} papers</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg" style={{ background: c.light, color: c.text, fontWeight: 600 }}>
                      <CheckCircle size={10} />Ready
                    </span>
                    <ChevronRight size={16} className="text-[#CBD5E1]" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Report viewer modal */}
      {viewingReport && (
        <div className="fixed inset-0 z-50 flex items-start justify-end"
          style={{ background: 'rgba(15,23,42,0.5)', backdropFilter: 'blur(4px)' }}
          onClick={e => { if (e.target === e.currentTarget) setViewingReport(null); }}>
          <div className="relative w-full max-w-3xl h-full bg-white overflow-hidden flex flex-col" style={{ boxShadow: '-8px 0 40px rgba(0,0,0,0.12)' }}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0] flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: `linear-gradient(145deg, ${PERIOD_COLORS[viewingReport.period]?.from ?? '#818CF8'}, ${PERIOD_COLORS[viewingReport.period]?.to ?? '#6366F1'})` }}>
                  <FileText size={14} color="white" />
                </div>
                <div>
                  <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{PERIODS.find(p => p.key === viewingReport.period)?.label} Report</p>
                  <p className="text-[#94A3B8] text-xs">{viewingReport.paper_count} papers · {fmtTime(viewingReport.generated_at)}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors" style={{ color: '#6366F1', fontWeight: 600 }}>
                  <Download size={13} />Export
                </button>
                <button onClick={() => setViewingReport(null)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center border border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors text-[#64748B]">
                  <X size={16} />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {viewingReport.content_html ? (
                <div dangerouslySetInnerHTML={{ __html: viewingReport.content_html }} />
              ) : (
                <div className="text-center py-12"><p className="text-[#94A3B8]">No content available for this report.</p></div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}