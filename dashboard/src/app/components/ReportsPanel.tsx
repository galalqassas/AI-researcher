import { useState, useEffect } from 'react';
import { renderToString } from 'react-dom/server';
import { FileText, Loader2, Clock, CheckCircle, ChevronRight, X, Download, Sparkles, AlertCircle, BookOpen, Layers, Globe, Brain, Bot, TrendingUp } from 'lucide-react';
import pdfIcon from '../../assets/pdfIcon.svg';
import { fetchReports, fetchReport, generateReport, type Report } from '../data/api';

const PERIODS = [
  { key: '7d', label: 'Last 7 Days', sub: 'Weekly digest' },
  { key: '1m', label: 'Last Month', sub: '~30 day window' },
  { key: '3m', label: 'Last 3 Months', sub: 'Quarterly view' },
  { key: '6m', label: 'Last 6 Months', sub: 'Half-year scan' },
  { key: '1y', label: 'Last Year', sub: 'Annual landscape' },
];

const PERIOD_COLORS: Record<string, { from: string; to: string; shadow: string; light: string; text: string; border: string }> = {
  '7d': { from: '#818CF8', to: '#6366F1', shadow: '#6366F1', light: '#EEF2FF', text: '#6366F1', border: '#C7D2FE' },
  '1m': { from: '#34D399', to: '#059669', shadow: '#10B981', light: '#ECFDF5', text: '#059669', border: '#A7F3D0' },
  '3m': { from: '#FCD34D', to: '#D97706', shadow: '#F59E0B', light: '#FFFBEB', text: '#D97706', border: '#FDE68A' },
  '6m': { from: '#FB7185', to: '#E11D48', shadow: '#F43F5E', light: '#FFF1F2', text: '#E11D48', border: '#FECDD3' },
  '1y': { from: '#A78BFA', to: '#7C3AED', shadow: '#8B5CF6', light: '#F5F3FF', text: '#7C3AED', border: '#DDD6FE' },
};

const BUCKET_META: Record<string, { label: string; icon: typeof BookOpen; emoji: string; gradFrom: string; gradTo: string; color: string; light: string; border: string }> = {
  general_ai:       { label: 'General AI',        emoji: '🧠', gradFrom: '#818CF8', gradTo: '#6366F1', icon: Brain,      color: '#6366F1', light: '#EEF2FF', border: '#C7D2FE' },
  autonomous_agents:{ label: 'Autonomous Agents', emoji: '🤖', gradFrom: '#34D399', gradTo: '#059669', icon: Bot,        color: '#059669', light: '#ECFDF5', border: '#A7F3D0' },
  ai_finance:       { label: 'AI + Finance',      emoji: '📈', gradFrom: '#FCD34D', gradTo: '#D97706', icon: TrendingUp, color: '#D97706', light: '#FFFBEB', border: '#FDE68A' },
};

const STAGE_MESSAGES: Record<number, string> = {
  0: 'Querying arXiv for papers…',
  1: 'Running hybrid classification (RRF + cosine)…',
  2: 'Generating per-paper summaries…',
  3: 'Synthesising bucket themes…',
  4: 'Building cross-domain analysis…',
};

function fmtTime(dt: string) {
  return new Date(dt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/* ─── Styled Report HTML ─────────────────────────────────────────────── */
const REPORT_CSS = `
  .report-body { font-family: inherit; color: #0F172A; }

  /* Bucket section card */
  .bucket-card {
    background: white; border: 1px solid #E2E8F0;
    border-radius: 16px; padding: 20px 22px; margin-bottom: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  }

  /* Bucket h2 header row */
  .report-body h2 {
    display: flex; align-items: center; gap: 10px;
    font-size: 1rem; font-weight: 700; color: #0F172A;
    margin: 0 0 4px; padding: 0; line-height: 1.3;
  }
  .bucket-icon {
    width: 32px; height: 32px; border-radius: 10px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0;
    box-shadow: 0 3px 8px rgba(0,0,0,0.15);
  }

  /* Section label ("5 papers in this category") */
  .report-body p em {
    font-style: normal; font-size: 0.72rem;
    color: #94A3B8; font-weight: 500;
  }
  .report-body p { font-size: 0.875rem; color: #475569; line-height: 1.7; margin: 0 0 10px; }

  /* Sub-heading (Key Themes / Important Papers) */
  .report-body h3 {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.09em;
    text-transform: uppercase; color: #94A3B8;
    margin: 16px 0 8px; padding: 0;
  }

  /* Paper list */
  .report-body ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 7px; }

  /* Each paper row — icon left, text right */
  .report-body li {
    background: #F8FAFC; border: 1px solid #E2E8F0;
    border-radius: 11px; padding: 10px 14px;
    display: flex; flex-direction: row; align-items: center; gap: 12px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .report-body li:hover { border-color: #C7D2FE; box-shadow: 0 2px 8px rgba(99,102,241,0.08); }

  /* Text block (title + date) */
  .paper-info {
    display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0;
  }
  .paper-title {
    font-size: 0.845rem; font-weight: 600; color: #0F172A;
    line-height: 1.4; display: block;
  }
  .paper-date {
    font-size: 0.72rem; color: #94A3B8; font-weight: 500;
  }
  .paper-pdf {
    display: inline-flex; align-items: center;
    transition: all 0.18s ease;
    text-decoration: none;
    flex-shrink: 0;
    padding: 5px 7px;
    border-radius: 10px;
    background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
    border: 1px solid #A5B4FC;
    box-shadow: 0 1px 3px rgba(99,102,241,0.15), 0 0 0 0 rgba(99,102,241,0);
    cursor: pointer;
  }
  .paper-pdf:hover { 
    transform: translateY(-1px) scale(1.04); 
    box-shadow: 0 4px 12px rgba(99,102,241,0.25), 0 0 0 2px rgba(99,102,241,0.15);
    border-color: #818CF8;
    background: linear-gradient(135deg, #E0E7FF 0%, #C7D2FE 100%);
  }
  .paper-pdf:active { transform: translateY(0) scale(0.98); }
  .pdf-icon-img { height: 24px; width: auto; filter: drop-shadow(0 1px 3px rgba(0,0,0,0.12)); }

  /* Cross-domain section */
  .cross-card {
    background: linear-gradient(135deg, #F5F3FF 0%, #EEF2FF 100%);
    border: 1px solid #DDD6FE; border-radius: 16px; padding: 20px 22px;
    box-shadow: 0 1px 4px rgba(124,58,237,0.06);
  }
  .cross-card h2 { color: #7C3AED; }
  .cross-card p { color: #3B0764; font-size: 0.875rem; line-height: 1.7; }
`;

function StyledReport({ html }: { html: string }) {
  return (
    <div>
      <style>{REPORT_CSS}</style>
      <div className="report-body" dangerouslySetInnerHTML={{ __html: transformReportHtml(html) }} />
    </div>
  );
}

/* Transform raw backend HTML into rich styled cards */
function transformReportHtml(raw: string): string {
  const bucketLabels: Record<string, string> = {
    'General AI': 'general_ai',
    'Autonomous Agents': 'autonomous_agents',
    'AI + Finance': 'ai_finance',
  };

  // Fix li elements: extract title (<strong>), date text and <a> link into separate rows
  const fixedLis = raw.replace(
    /<li><strong>([^<]+)<\/strong>\s*\(([^)]+)\)\s*(?:—\s*)?(<a[^>]+>PDF<\/a>|\(no PDF\))<\/li>/g,
    (_m, title, date, pdfHtml) => {
      const pdfBadge = pdfHtml.startsWith('<a')
        ? pdfHtml.replace('<a ', '<a class="paper-pdf" title="View PDF" ').replace('>PDF<', `><img src="${pdfIcon}" class="pdf-icon-img" alt="PDF" /><`)
        : '';
      return `<li>${pdfBadge}<div class="paper-info"><span class="paper-title">${title}</span><span class="paper-date">${date}</span></div></li>`;
    }
  );

  // Split on <hr>\n to get sections
  const parts = fixedLis.split(/<hr>\n?/).filter(Boolean);

  return parts.map((part) => {
    const isCross = part.includes('Cross-Domain');
    if (isCross) {
      // Hide the section if the LLM couldn't produce a real synthesis
      if (part.toLowerCase().includes('unavailable')) return '';
      return `<div class="cross-card">${part}</div>`;
    }

    // Identify bucket
    let bucketKey = 'general_ai';
    for (const [label, key] of Object.entries(bucketLabels)) {
      if (part.includes(`<h2>${label}</h2>`)) { bucketKey = key; break; }
    }
    const meta = BUCKET_META[bucketKey];

    // Build gradient icon badge using lucide-react icon
    const iconSvg = renderToString(<meta.icon size={18} color="white" />);
    const iconBadge = `<span class="bucket-icon" style="background:linear-gradient(145deg,${meta.gradFrom},${meta.gradTo})">${iconSvg}</span>`;

    // Inject icon into h2
    const styled = part.replace(
      /(<h2>)([^<]+)(<\/h2>)/,
      `$1${iconBadge} $2$3`
    );

    return `<div class="bucket-card">${styled}</div>`;
  }).join('');
}

/* ─── Report Viewer Modal ─────────────────────────────────────────────── */
function ReportModal({ report, onClose }: { report: Report; onClose: () => void }) {
  const c = PERIOD_COLORS[report.period] ?? PERIOD_COLORS['7d'];
  const periodLabel = PERIODS.find(p => p.key === report.period)?.label ?? report.period;

  function handleExport() {
    if (!report.content_html) return;
    const blob = new Blob([`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${periodLabel} Report</title></head><body style="font-family:system-ui,sans-serif;max-width:780px;margin:40px auto;padding:0 20px">${report.content_html}</body></html>`], { type: 'text/html' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `report-${report.period}-${report.id}.html`;
    a.click();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(15,23,42,0.55)', backdropFilter: 'blur(6px)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Floating window */}
      <div
        className="relative flex flex-col bg-white overflow-hidden"
        style={{
          width: '100%',
          maxWidth: '760px',
          height: '82vh',
          maxHeight: '820px',
          borderRadius: '20px',
          boxShadow: '0 32px 80px rgba(0,0,0,0.22), 0 0 0 1px rgba(0,0,0,0.06)',
          animation: 'modalIn 0.22s cubic-bezier(0.34,1.56,0.64,1)',
        }}
      >
        <style>{`
          @keyframes modalIn {
            from { opacity: 0; transform: scale(0.94) translateY(12px); }
            to   { opacity: 1; transform: scale(1) translateY(0); }
          }
        `}</style>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 flex-shrink-0 border-b border-[#F1F5F9]">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: `linear-gradient(145deg, ${c.from}, ${c.to})`, boxShadow: `0 4px 14px ${c.shadow}45` }}
            >
              <FileText size={16} color="white" />
            </div>
            <div>
              <p className="text-[#0F172A] text-sm" style={{ fontWeight: 700, lineHeight: 1.2 }}>{periodLabel} Report</p>
              <p className="text-[#94A3B8] text-xs mt-0.5">{report.paper_count} papers · {fmtTime(report.generated_at)}</p>
            </div>
          </div>

          {/* Pills */}
          <div className="flex items-center gap-2">
            <span
              className="text-xs px-2.5 py-1 rounded-lg flex items-center gap-1.5"
              style={{
                background: c.light, color: c.text, fontWeight: 600,
                border: `1px solid ${c.border}`,
                transition: 'transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease',
                cursor: 'default',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.transform = 'scale(1.05)';
                (e.currentTarget as HTMLElement).style.boxShadow = `0 3px 10px ${c.shadow}50`;
                (e.currentTarget as HTMLElement).style.background = c.border;
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
                (e.currentTarget as HTMLElement).style.background = c.light;
              }}
            >
              <CheckCircle size={11} /> Ready
            </span>
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs border border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors"
              style={{ color: '#6366F1', fontWeight: 600 }}
            >
              <Download size={12} /> Export
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-xl border border-[#E2E8F0] flex items-center justify-center hover:bg-[#F8FAFC] transition-colors text-[#94A3B8] hover:text-[#475569]"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Bucket summary strip */}
        <div className="flex gap-2 px-6 py-3 border-b border-[#F1F5F9] flex-shrink-0 overflow-x-auto">
          {Object.entries(BUCKET_META).map(([key, meta]) => (
            <div
              key={key}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl flex-shrink-0"
              style={{
                background: meta.light,
                border: `1px solid ${meta.border}`,
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                cursor: 'default',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
                (e.currentTarget as HTMLElement).style.boxShadow = `0 6px 16px ${meta.color}30`;
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(0)';
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
              }}
            >
              <span
                className="w-5 h-5 rounded-md flex items-center justify-center text-xs flex-shrink-0"
                style={{
                  background: `linear-gradient(145deg, ${meta.gradFrom}, ${meta.gradTo})`,
                  boxShadow: `0 2px 6px ${meta.color}40`,
                }}
              >
                <meta.icon size={12} color="white" />
              </span>
              <span className="text-xs" style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
            </div>
          ))}
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-5" style={{ scrollbarWidth: 'thin', scrollbarColor: '#E2E8F0 transparent' }}>
          {report.content_html ? (
            <StyledReport html={report.content_html} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full py-16 gap-3">
              <FileText size={36} className="text-[#CBD5E1]" />
              <p className="text-[#94A3B8] text-sm">No content available for this report.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Main Panel ─────────────────────────────────────────────────────── */
export function ReportsPanel() {
  const [generating, setGenerating] = useState<string | null>(null);
  const [stage, setStage] = useState(0);
  const [viewingReport, setViewingReport] = useState<Report | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingError, setGeneratingError] = useState<string | null>(null);

  useEffect(() => {
    fetchReports().then(setReports).catch(() => {}).finally(() => setLoading(false));
  }, []);

  async function handleGenerate(period: string) {
    setGenerating(period);
    setStage(0);
    setGeneratingError(null);
    const interval = setInterval(() => setStage(s => Math.min(s + 1, 4)), 1500);
    try {
      const result = await generateReport(period);
      const updated = await fetchReports();
      setReports(updated);
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

  async function handleOpenReport(report: Report) {
    // Fetch full content if not already loaded
    if (!report.content_html) {
      try {
        const full = await fetchReport(report.id);
        setViewingReport(full);
      } catch { setViewingReport(report); }
    } else {
      setViewingReport(report);
    }
  }

  const pc = (p: string) => PERIOD_COLORS[p] ?? PERIOD_COLORS['7d'];

  return (
    <div className="p-6 space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-[#0F172A]" style={{ fontWeight: 700 }}>Research Reports</h1>
        <p className="text-[#64748B] text-sm mt-0.5">Generate LLM-powered digests grouped by research bucket with cross-domain synthesis</p>
      </div>

      {/* Error banner */}
      {generatingError && (
        <div className="flex items-start gap-3 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
          <AlertCircle size={16} className="text-rose-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-rose-700 text-sm" style={{ fontWeight: 600 }}>Generation failed</p>
            <p className="text-rose-600 text-xs mt-0.5">{generatingError}</p>
          </div>
        </div>
      )}

      {/* Generate new report */}
      <div>
        <h3 className="text-[#475569] text-xs mb-3" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
          Generate New Report
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
          {PERIODS.map(({ key, label, sub }) => {
            const isGenerating = generating === key;
            const c = pc(key);
            const existingReport = reports.find(r => r.period === key);
            return (
              <button
                key={key}
                onClick={() => !generating && handleGenerate(key)}
                disabled={!!generating}
                className="group relative flex flex-col items-start p-4 rounded-2xl border text-left transition-all duration-200 hover:shadow-md focus:outline-none"
                style={{
                  background: isGenerating ? c.light : 'white',
                  borderColor: isGenerating ? c.border : '#E2E8F0',
                  opacity: generating && !isGenerating ? 0.45 : 1,
                  cursor: generating ? 'not-allowed' : 'pointer',
                  boxShadow: isGenerating ? `0 0 0 2px ${c.border}` : undefined,
                }}
              >
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center mb-3"
                  style={{ background: `linear-gradient(145deg, ${c.from}, ${c.to})`, boxShadow: `0 4px 12px ${c.shadow}40` }}
                >
                  {isGenerating ? <Loader2 size={15} color="white" className="animate-spin" /> : <Sparkles size={15} color="white" />}
                </div>
                <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{label}</p>
                <p className="text-[#94A3B8] text-xs mt-0.5">{sub}</p>

                {isGenerating && (
                  <div className="mt-3 w-full">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Loader2 size={10} style={{ color: c.text }} className="animate-spin" />
                      <span className="text-xs" style={{ color: c.text, lineHeight: 1.3 }}>{STAGE_MESSAGES[stage]}</span>
                    </div>
                    <div className="h-1 rounded-full bg-gray-100 overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${((stage + 1) / 5) * 100}%`, background: `linear-gradient(90deg, ${c.from}, ${c.to})` }} />
                    </div>
                    <p className="text-right text-xs mt-1" style={{ color: c.text }}>Stage {stage + 1} / 5</p>
                  </div>
                )}

                {!isGenerating && existingReport && (
                  <p className="mt-2 text-xs" style={{ color: c.text }}>
                    Last: {fmtTime(existingReport.generated_at)}
                  </p>
                )}

                {!isGenerating && (
                  <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: c.text }}>
                    <ChevronRight size={13} />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Cost tip */}
      <div className="flex items-start gap-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-3">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'linear-gradient(145deg, #818CF8, #6366F1)' }}>
          <span className="text-white" style={{ fontSize: '0.75rem' }}>💡</span>
        </div>
        <div>
          <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>Cost-aware generation</p>
          <p className="text-[#64748B] text-xs mt-0.5">
            Per-paper summaries use the light model. Bucket &amp; cross-domain synthesis use the heavy model. LLM responses are SHA-256 cached — repeat runs are free.
          </p>
        </div>
      </div>

      {/* Report history */}
      <div>
        <h3 className="text-[#475569] text-xs mb-3" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
          Report History
        </h3>
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="animate-spin text-[#6366F1]" size={22} />
          </div>
        ) : reports.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[#E2E8F0] p-10 text-center">
            <FileText size={30} className="text-[#CBD5E1] mx-auto mb-2" />
            <p className="text-[#94A3B8] text-sm">No reports yet — generate one above</p>
          </div>
        ) : (
          <div className="space-y-2">
            {reports.map(report => {
              const c = pc(report.period);
              const periodLabel = PERIODS.find(p => p.key === report.period)?.label ?? report.period;
              return (
                <div
                  key={report.id}
                  className="bg-white rounded-2xl border border-[#E2E8F0] p-4 flex items-center gap-4 hover:shadow-sm hover:border-[#C7D2FE] transition-all cursor-pointer group"
                  onClick={() => handleOpenReport(report)}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: `linear-gradient(145deg, ${c.from}, ${c.to})`, boxShadow: `0 4px 12px ${c.shadow}30` }}
                  >
                    <FileText size={15} color="white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[#0F172A] text-sm" style={{ fontWeight: 600 }}>{periodLabel} Report</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="flex items-center gap-1 text-xs text-[#94A3B8]"><Clock size={10} />{fmtTime(report.generated_at)}</span>
                      <span className="flex items-center gap-1 text-xs text-[#94A3B8]"><FileText size={10} />{report.paper_count} papers</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg" style={{ background: c.light, color: c.text, fontWeight: 600, border: `1px solid ${c.border}` }}>
                      <CheckCircle size={10} /> Ready
                    </span>
                    <ChevronRight size={15} className="text-[#CBD5E1] group-hover:text-[#6366F1] transition-colors" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Floating report modal */}
      {viewingReport && <ReportModal report={viewingReport} onClose={() => setViewingReport(null)} />}
    </div>
  );
}