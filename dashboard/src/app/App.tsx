import { useState, useEffect, lazy, Suspense } from 'react';
import {
  LayoutDashboard, FileText, BookOpen, Activity, Search,
  ChevronRight, Brain, Bell, Loader2,
} from 'lucide-react';
import { searchPapers, fetchPipelineRuns, fetchPaperStats, type PipelineRun, type SearchResult } from './data/api';
import { usePollingEffect, getAdaptiveInterval } from './hooks/usePolling';
import { ErrorBoundary } from './components/ErrorBoundary';

const DashboardHome = lazy(() => import('./components/DashboardHome'));
const ReportsPanel = lazy(() => import('./components/ReportsPanel'));
const PapersPanel = lazy(() => import('./components/PapersPanel'));
const PipelinePanel = lazy(() => import('./components/PipelinePanel'));

type Page = 'dashboard' | 'reports' | 'papers' | 'pipeline';

const NAV = [
  { key: 'dashboard' as Page, label: 'Dashboard', icon: LayoutDashboard },
  { key: 'reports' as Page, label: 'Reports', icon: FileText },
  { key: 'papers' as Page, label: 'Papers', icon: BookOpen },
  { key: 'pipeline' as Page, label: 'Pipeline', icon: Activity },
];

function SearchPapersInline({ onClose, onNavigate }: { onClose: () => void; onNavigate: (arxivId: string) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await searchPapers(query, 6);
        setResults(data.data.results);
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
              <div key={paper.id} className="flex items-start gap-3 px-4 py-3 hover:bg-[#F8FAFC] cursor-pointer transition-colors" onClick={() => { onNavigate(paper.arxiv_id); onClose(); }}>
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
            <p className="text-[#334155] text-sm mb-3" style={{ fontWeight: 600, letterSpacing: '0.01em' }}>
              Search papers using Hybrid BM25 + Vector Search
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
  const [searchNav, setSearchNav] = useState<{query: string; nonce: number}>({query: '', nonce: 0});
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [totalPapers, setTotalPapers] = useState(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const runInterval = getAdaptiveInterval(pipelineRuns);

  const loadSidebarData = async () => {
    const [runsResult, statsResult] = await Promise.all([
      fetchPipelineRuns(1).catch(() => ({ data: [] as PipelineRun[], fromCache: false })),
      fetchPaperStats().catch(() => ({ data: null as any, fromCache: false })),
    ]);
    setPipelineRuns(runsResult.data);
    if (statsResult.data) setTotalPapers(statsResult.data.total);
  };

  useEffect(() => { loadSidebarData(); }, []);
  usePollingEffect(loadSidebarData, runInterval);

  const lastRun = pipelineRuns[0];

  return (
    <div className="flex h-screen bg-[#F8FAFC] overflow-hidden">
      {/* Sidebar */}
      <aside
        className="flex-shrink-0 bg-white border-r border-[#E2E8F0] flex flex-col h-full"
        style={{ width: sidebarCollapsed ? '64px' : '240px', transition: 'width 0.2s ease-out' }}
      >
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
            {!sidebarCollapsed && (
              <div>
                <p className="text-[#0F172A] text-sm" style={{ fontWeight: 700 }}>Auto-Researcher</p>
                <p className="text-[#94A3B8]" style={{ fontSize: '0.7rem' }}>arXiv Intelligence MVP</p>
              </div>
            )}
          </div>
        </div>

        {/* Search shortcut */}
        <div className="px-3 pt-4 pb-2" style={{ display: sidebarCollapsed ? 'none' : 'block' }}>
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
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 0, padding: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '0 4px 8px' }}>
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              style={{
                width: 28, height: 28, borderRadius: 8,
                border: '1px solid #E2E8F0', background: 'white',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', transition: 'all 0.15s ease-out', color: '#94A3B8',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#F8FAFC'; e.currentTarget.style.borderColor = '#CBD5E1'; e.currentTarget.style.color = '#64748B'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.borderColor = '#E2E8F0'; e.currentTarget.style.color = '#94A3B8'; }}
              title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: sidebarCollapsed ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease-out' }}><polyline points="15 18 9 12 15 6" /></svg>
            </button>
          </div>
          {NAV.slice(0, 2).map(({ key, label, icon: Icon }) => {
            const active = page === key;
            return (
              <button
                key={key}
                onClick={() => {
                  setPage(key);
                  if (key === 'papers') setSearchNav(prev => ({ query: '', nonce: prev.nonce + 1 }));
                }}
                className="sidebar-nav-item"
                style={{
                  width: '100%', display: 'flex', alignItems: 'center',
                  gap: sidebarCollapsed ? 0 : 12,
                  padding: sidebarCollapsed ? '10px' : '9px 12px',
                  borderRadius: 10, border: 'none', background: active ? '#030213' : 'transparent',
                  color: active ? 'white' : '#64748B', cursor: 'pointer',
                  transition: 'all 0.15s ease-out', textAlign: 'left',
                  fontSize: 13.5, fontWeight: active ? 500 : 400,
                  justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = '#F8FAFC'; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon size={14} color={active ? 'white' : '#94A3B8'} />
                </div>
                {!sidebarCollapsed && <span className="nav-label" style={{ whiteSpace: 'nowrap', overflow: 'hidden' }}>{label}</span>}
              </button>
            );
          })}
          {!sidebarCollapsed && <div style={{ height: 1, background: '#F1F5F9', margin: '6px 8px' }} />}
          {NAV.slice(2).map(({ key, label, icon: Icon }) => {
            const active = page === key;
            return (
              <button
                key={key}
                onClick={() => {
                  setPage(key);
                  if (key === 'papers') setSearchNav(prev => ({ query: '', nonce: prev.nonce + 1 }));
                }}
                className="sidebar-nav-item"
                style={{
                  width: '100%', display: 'flex', alignItems: 'center',
                  gap: sidebarCollapsed ? 0 : 12,
                  padding: sidebarCollapsed ? '10px' : '9px 12px',
                  borderRadius: 10, border: 'none', background: active ? '#030213' : 'transparent',
                  color: active ? 'white' : '#64748B', cursor: 'pointer',
                  transition: 'all 0.15s ease-out', textAlign: 'left',
                  fontSize: 13.5, fontWeight: active ? 500 : 400,
                  justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = '#F8FAFC'; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon size={14} color={active ? 'white' : '#94A3B8'} />
                </div>
                {!sidebarCollapsed && <span className="nav-label" style={{ whiteSpace: 'nowrap', overflow: 'hidden' }}>{label}</span>}
                {!sidebarCollapsed && key === 'papers' && totalPapers > 0 && (
                  <span style={{ marginLeft: 'auto', fontSize: 11, padding: '2px 7px', borderRadius: 5, fontWeight: 600, background: active ? 'rgba(255,255,255,0.2)' : '#F1F5F9', color: active ? 'rgba(255,255,255,0.9)' : '#94A3B8' }}>
                    {totalPapers}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        

        {/* System status (Hidden per request) */}
        {/* <div className="px-3 py-4 border-t border-[#F1F5F9]"> ... </div> */}

        {/* Last run footer (Hidden per request) */}
        {/* lastRun && <div ...> ... </div> */}
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
            <button className="hidden relative w-8 h-8 rounded-xl border border-[#E2E8F0] flex items-center justify-center hover:bg-[#F8FAFC] transition-colors">
              <Bell size={14} className="text-[#64748B]" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto">
          <ErrorBoundary>
            <Suspense fallback={
              <div className="flex items-center justify-center h-full">
                <Loader2 className="animate-spin text-[#6366F1]" size={24} />
              </div>
            }>
              {page === 'dashboard' && <DashboardHome />}
              {page === 'reports' && <ReportsPanel />}
              {page === 'papers' && <PapersPanel key={searchNav.nonce} onPapersLoaded={setTotalPapers} initialQuery={searchNav.query} />}
              {page === 'pipeline' && <PipelinePanel />}
            </Suspense>
          </ErrorBoundary>
        </div>
      </main>

      {/* Search modal */}
      {searchOpen && <SearchPapersInline onClose={() => setSearchOpen(false)} onNavigate={(arxivId) => { setSearchNav(prev => ({query: arxivId, nonce: prev.nonce + 1})); setPage('papers'); setSearchOpen(false); }} />}
    </div>
  );
}
