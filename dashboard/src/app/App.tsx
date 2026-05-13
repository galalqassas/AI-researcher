import { useState, useEffect } from 'react';
import {
  LayoutDashboard, FileText, BookOpen, Activity, Search,
  ChevronRight, Brain, Settings, Bell,
} from 'lucide-react';
import { DashboardHome } from './components/DashboardHome';
import { ReportsPanel } from './components/ReportsPanel';
import { PapersPanel } from './components/PapersPanel';
import { PipelinePanel } from './components/PipelinePanel';
import { searchPapers, fetchPipelineRuns, BUCKET_CONFIG, type PipelineRun, type SearchResult } from './data/api';

type Page = 'dashboard' | 'reports' | 'papers' | 'pipeline';

const NAV = [
  { key: 'dashboard' as Page, label: 'Dashboard', icon: LayoutDashboard },
  { key: 'reports' as Page, label: 'Reports', icon: FileText },
  { key: 'papers' as Page, label: 'Papers', icon: BookOpen },
  { key: 'pipeline' as Page, label: 'Pipeline', icon: Activity },
];

function SearchPapersInline({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await searchPapers(query, 6);
        setResults(data.results);
      } catch { setResults([]); }
      finally { setLoading(false); }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4"
      style={{ background: 'rgba(15,23,42,0.5)', backdropFilter: 'blur(4px)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-2xl bg-white rounded-2xl overflow-hidden" style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-[#F1F5F9]">
          <Search size={16} className="text-[#94A3B8]" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search papers by title, abstract, or arXiv ID…"
            className="flex-1 text-sm text-[#0F172A] outline-none placeholder:text-[#CBD5E1] bg-transparent"
          />
          <kbd className="text-[#94A3B8] text-xs px-1.5 py-0.5 rounded border border-[#E2E8F0]">Esc</kbd>
        </div>
        {loading && (
          <div className="px-4 py-6 text-center text-[#94A3B8] text-sm">Searching…</div>
        )}
        {!loading && query && results.length === 0 && (
          <div className="px-4 py-8 text-center text-[#94A3B8] text-sm">No papers found for "{query}"</div>
        )}
        {results.length > 0 && (
          <div className="divide-y divide-[#F1F5F9] max-h-96 overflow-y-auto">
            {results.map(paper => (
              <div key={paper.id} className="flex items-start gap-3 px-4 py-3 hover:bg-[#F8FAFC] cursor-pointer transition-colors" onClick={onClose}>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5" style={{ background: '#EEF2FF' }}>
                  <BookOpen size={13} style={{ color: '#6366F1' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[#0F172A] text-sm truncate" style={{ fontWeight: 500 }}>{paper.title}</p>
                  <p className="text-[#94A3B8] text-xs mt-0.5">arXiv:{paper.arxiv_id} · Score: {paper.score}</p>
                </div>
                <ChevronRight size={14} className="text-[#CBD5E1] mt-1 flex-shrink-0" />
              </div>
            ))}
          </div>
        )}
        {!query && (
          <div className="px-4 py-6">
            <p className="text-[#94A3B8] text-xs mb-3" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Type to search papers using hybrid BM25 + vector search
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [searchOpen, setSearchOpen] = useState(false);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [totalPapers, setTotalPapers] = useState(0);
  const [runsLoaded, setRunsLoaded] = useState(false);

  useEffect(() => {
    fetchPipelineRuns(1).then(runs => {
      setPipelineRuns(runs);
      setRunsLoaded(true);
    }).catch(() => setRunsLoaded(true));
  }, []);

  // Listen for custom events to refresh sidebar data
  useEffect(() => {
    const refresh = () => {
      fetchPipelineRuns(1).then(setPipelineRuns).catch(() => {});
    };
    window.addEventListener('pipeline-refresh', refresh);
    window.addEventListener('papers-refresh', () => {
      // Re-fetch is handled by individual panels
    });
    return () => { window.removeEventListener('pipeline-refresh', refresh); };
  }, []);

  const lastRun = pipelineRuns[0];
  const successRuns = pipelineRuns.filter(r => r.status === 'success');

  // Allow child components to update paper count
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (typeof detail === 'number') setTotalPapers(detail);
    };
    window.addEventListener('paper-count', handler);
    return () => window.removeEventListener('paper-count', handler);
  }, []);

  return (
    <div className="flex h-screen bg-[#F8FAFC] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 bg-white border-r border-[#E2E8F0] flex flex-col h-full">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-[#F1F5F9]">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{
                background: 'linear-gradient(145deg, #818CF8, #6366F1)',
                boxShadow: '0 6px 16px #6366F140, inset 0 1px 1px rgba(255,255,255,0.35)',
              }}
            >
              <Brain size={18} color="white" />
            </div>
            <div>
              <p className="text-[#0F172A] text-sm" style={{ fontWeight: 700 }}>Auto-Researcher</p>
              <p className="text-[#94A3B8]" style={{ fontSize: '0.7rem' }}>arXiv Intelligence MVP</p>
            </div>
          </div>
        </div>

        {/* Search shortcut */}
        <div className="px-3 pt-4 pb-2">
          <button
            onClick={() => setSearchOpen(true)}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] hover:bg-[#F1F5F9] transition-colors text-left"
          >
            <Search size={13} className="text-[#94A3B8]" />
            <span className="text-[#CBD5E1] text-sm flex-1">Search papers…</span>
            <kbd className="text-[#CBD5E1]" style={{ fontSize: '0.65rem' }}>⌘K</kbd>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-0.5">
          <p className="px-2 pb-1 pt-2 text-[#94A3B8]" style={{ fontSize: '0.68rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            Navigation
          </p>
          {NAV.map(({ key, label, icon: Icon }) => {
            const active = page === key;
            return (
              <button
                key={key}
                onClick={() => setPage(key)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-left group"
                style={{
                  background: active ? 'linear-gradient(135deg, #EEF2FF, #F5F3FF)' : 'transparent',
                  color: active ? '#6366F1' : '#64748B',
                }}
              >
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition-all"
                  style={{
                    background: active ? 'linear-gradient(145deg, #818CF8, #6366F1)' : 'transparent',
                    boxShadow: active ? '0 3px 8px #6366F130' : 'none',
                  }}
                >
                  <Icon size={14} color={active ? 'white' : '#94A3B8'} />
                </div>
                <span
                  className="text-sm transition-colors"
                  style={{ fontWeight: active ? 600 : 400, color: active ? '#6366F1' : '#64748B' }}
                >
                  {label}
                </span>
                {key === 'papers' && totalPapers > 0 && (
                  <span
                    className="ml-auto text-xs px-1.5 py-0.5 rounded-md"
                    style={{
                      background: active ? '#6366F120' : '#F1F5F9',
                      color: active ? '#6366F1' : '#94A3B8',
                      fontWeight: 600,
                    }}
                  >
                    {totalPapers}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* System status */}
        <div className="px-3 py-4 border-t border-[#F1F5F9]">
          <p className="px-2 pb-2 text-[#94A3B8]" style={{ fontSize: '0.68rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
            System Status
          </p>
          {[
            { label: 'API Server', status: true, detail: window.location.origin },
            { label: 'DB Queue', status: true, detail: `${totalPapers || '—'} papers` },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2 px-2 py-1">
              <div
                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${item.status ? 'bg-emerald-400' : 'bg-rose-400'}`}
                style={{ boxShadow: item.status ? '0 0 4px #34D399' : '0 0 4px #F87171' }}
              />
              <span className="text-[#475569]" style={{ fontSize: '0.75rem', fontWeight: 500 }}>
                {item.label}
              </span>
              <span className="text-[#CBD5E1] ml-auto" style={{ fontSize: '0.65rem' }}>
                {item.detail}
              </span>
            </div>
          ))}
        </div>

        {/* Last run footer */}
        {lastRun && (
          <div
            className="mx-3 mb-3 rounded-xl p-3 border"
            style={{
              background: lastRun.status === 'success' ? '#ECFDF5' : '#FFF1F2',
              borderColor: lastRun.status === 'success' ? '#A7F3D0' : '#FECDD3',
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <div
                className="w-1.5 h-1.5 rounded-full"
                style={{
                  background: lastRun.status === 'success' ? '#10B981' : '#F43F5E',
                  boxShadow: lastRun.status === 'success' ? '0 0 4px #10B981' : '0 0 4px #F43F5E',
                }}
              />
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: lastRun.status === 'success' ? '#059669' : '#E11D48',
                }}
              >
                Last run {lastRun.status}
              </span>
            </div>
            <p className="text-[#64748B]" style={{ fontSize: '0.68rem' }}>
              {lastRun.name.replace(/_/g, ' ')} ·{' '}
              {lastRun.duration_s ? `${(lastRun.duration_s / 60).toFixed(1)}m` : '—'}
            </p>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top header bar */}
        <header className="bg-white border-b border-[#E2E8F0] px-6 py-3.5 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-[#94A3B8]">Auto-Researcher</span>
            <ChevronRight size={14} className="text-[#CBD5E1]" />
            <span className="text-[#0F172A]" style={{ fontWeight: 600 }}>
              {NAV.find(n => n.key === page)?.label}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {totalPapers > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[#64748B] text-xs" style={{ fontWeight: 500 }}>
                  {totalPapers} papers
                </span>
              </div>
            )}
            <button
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] transition-colors"
            >
              <Search size={13} className="text-[#94A3B8]" />
              <span className="text-[#94A3B8] text-xs">Search</span>
            </button>
            <button className="relative w-8 h-8 rounded-xl border border-[#E2E8F0] flex items-center justify-center hover:bg-[#F8FAFC] transition-colors">
              <Bell size={14} className="text-[#64748B]" />
            </button>
            <button className="w-8 h-8 rounded-xl border border-[#E2E8F0] flex items-center justify-center hover:bg-[#F8FAFC] transition-colors">
              <Settings size={14} className="text-[#64748B]" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto">
          {page === 'dashboard' && <DashboardHome onPapersLoaded={setTotalPapers} />}
          {page === 'reports' && <ReportsPanel />}
          {page === 'papers' && <PapersPanel onPapersLoaded={setTotalPapers} />}
          {page === 'pipeline' && <PipelinePanel />}
        </div>
      </main>

      {/* Search modal */}
      {searchOpen && <SearchPapersInline onClose={() => setSearchOpen(false)} />}
    </div>
  );
}