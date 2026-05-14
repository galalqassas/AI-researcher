import { useState, useMemo, useEffect, useRef } from 'react';
import { Search, ExternalLink, ChevronDown, ChevronUp, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { fetchPapers, BUCKET_CONFIG, type BucketKey, type Paper } from '../data/api';

const ALL_BUCKET_KEYS = Object.keys(BUCKET_CONFIG) as BucketKey[];
const PAGE_SIZES = [10, 20, 50] as const;
type PageSize = typeof PAGE_SIZES[number];

function highlight(text: string, q: string) {
  const t = q.trim();
  if (!t) return text;
  const parts = text.split(new RegExp(`(${t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return parts.map((p, i) =>
    i % 2 === 1
      ? <mark key={i} style={{ background: '#FEF9C3', color: '#0F172A', borderRadius: '2px', padding: '0 1px' }}>{p}</mark>
      : p
  );
}

function PaperCard({ paper, query }: { paper: Paper; query: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-white rounded-2xl border border-[#E2E8F0] p-5 hover:shadow-md transition-all duration-200">
      <div className="flex items-start gap-4">
        <div className="flex flex-col gap-1 pt-1 flex-shrink-0">
          {paper.buckets.map(b => (
            <div key={b} className="w-2.5 h-2.5 rounded-full" style={{ background: BUCKET_CONFIG[b]?.color }} title={BUCKET_CONFIG[b]?.label} />
          ))}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <h4>
              <a
                href={`https://arxiv.org/abs/${paper.arxiv_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#0F172A] hover:text-[#6366F1] hover:underline transition-colors duration-200"
                style={{ fontWeight: 600 }}
              >
                {highlight(paper.title, query)}
              </a>
            </h4>
            <a href={`https://arxiv.org/abs/${paper.arxiv_id}`} target="_blank" rel="noopener noreferrer"
              className="flex-shrink-0 w-7 h-7 rounded-lg border border-[#E2E8F0] flex items-center justify-center text-[#94A3B8] hover:text-[#6366F1] hover:border-[#6366F1] transition-colors">
              <ExternalLink size={13} />
            </a>
          </div>
          <p className="text-[#94A3B8] text-xs mt-1">
            {paper.authors || 'Unknown authors'} · {paper.published_date || '—'} · <span className="font-mono">arXiv:{paper.arxiv_id}</span>
          </p>
          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
            {paper.buckets.map(b => {
              const cfg = BUCKET_CONFIG[b];
              return (
                <span key={b} className="text-xs px-2 py-0.5 rounded-full"
                  style={{ background: cfg.colorLight, color: cfg.color, fontWeight: 600, border: `1px solid ${cfg.color}25` }}>
                  {cfg.label}
                </span>
              );
            })}
          </div>
          {paper.abstract && (
            <div className="mt-3">
              <p className={`text-[#475569] text-sm ${open ? '' : 'line-clamp-2'}`}>{highlight(paper.abstract, query)}</p>
              <button type="button" onClick={() => setOpen(v => !v)}
                className="flex items-center gap-1 text-xs mt-1.5 text-[#6366F1] hover:text-[#4F46E5] transition-colors"
                style={{ fontWeight: 600 }}>
                {open ? <><ChevronUp size={12} /> Show less</> : <><ChevronDown size={12} /> Read more</>}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function PapersPanel({ onPapersLoaded, initialQuery }: { onPapersLoaded?: (count: number) => void; initialQuery?: string }) {
  const [bucket, setBucket] = useState<BucketKey | 'all'>('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<PageSize>(20);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [total, setTotal] = useState(0);
  const [initialLoad, setInitialLoad] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState(initialQuery ?? '');
  const [serverSearch, setServerSearch] = useState(initialQuery ?? '');

  const cbRef = useRef(onPapersLoaded);
  cbRef.current = onPapersLoaded;

  useEffect(() => {
    let cancelled = false;
    setFetching(true);
    setError(null);
    fetchPapers(bucket === 'all' ? undefined : bucket, page, pageSize, serverSearch || undefined)
      .then(data => {
        if (cancelled) return;
        setPapers(data.results);
        setTotal(data.total);
        cbRef.current?.(data.total);
      })
      .catch(e => { if (!cancelled) setError(String(e?.message ?? e)); })
      .finally(() => { 
        if (!cancelled) {
          setFetching(false);
          setInitialLoad(false);
        }
      });
    return () => { cancelled = true; };
  }, [bucket, page, pageSize, serverSearch]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setServerSearch(query);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const goTo = (n: number) => setPage(Math.min(Math.max(1, n), totalPages));

  const pageNums = useMemo(() => {
    const s = Math.max(1, page - 2), e = Math.min(totalPages, page + 2);
    return Array.from({ length: e - s + 1 }, (_, i) => s + i);
  }, [page, totalPages]);

  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  const btnPage = (n: number, label: React.ReactNode = n) => (
    <button key={String(n)} type="button" onClick={() => goTo(n)}
      className="w-8 h-8 rounded-lg border text-xs transition-all"
      style={{ background: n === page ? '#0F172A' : 'white', color: n === page ? 'white' : '#64748B', border: `1px solid ${n === page ? '#0F172A' : '#E2E8F0'}`, fontWeight: n === page ? 600 : 400 }}>
      {label}
    </button>
  );

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-[#0F172A]" style={{ fontWeight: 700 }}>Papers</h1>
        <p className="text-[#64748B] text-sm mt-0.5">Browse all ingested arXiv papers · filter by bucket</p>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
          <input type="text" value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Search papers by title, abstract, arXiv ID…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[#E2E8F0] bg-white text-sm text-[#0F172A] placeholder:text-[#CBD5E1] focus:outline-none focus:ring-2 focus:ring-[#6366F1]/30 focus:border-[#6366F1] transition-all" />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <button type="button" onClick={() => { setBucket('all'); setPage(1); setQuery(''); setServerSearch(''); }}
            className="px-3 py-2 rounded-xl text-sm transition-all"
            style={{ background: bucket === 'all' ? '#0F172A' : 'white', color: bucket === 'all' ? 'white' : '#64748B', border: `1px solid ${bucket === 'all' ? '#0F172A' : '#E2E8F0'}`, fontWeight: bucket === 'all' ? 600 : 400 }}>
            All ({total})
          </button>
          {ALL_BUCKET_KEYS.map(key => {
            const cfg = BUCKET_CONFIG[key];
            const active = bucket === key;
            return (
              <button key={key} type="button" onClick={() => { setBucket(key); setPage(1); setQuery(''); setServerSearch(''); }}
                className="px-3 py-2 rounded-xl text-sm transition-all flex items-center gap-1.5"
                style={{ background: active ? cfg.colorLight : 'white', color: active ? cfg.color : '#64748B', border: `1px solid ${active ? `${cfg.color}50` : '#E2E8F0'}`, fontWeight: active ? 600 : 400 }}>
                <div className="w-2 h-2 rounded-full" style={{ background: cfg.color }} />
                {cfg.label}
              </button>
            );
          })}
        </div>
      </div>

      {initialLoad ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="animate-spin text-[#6366F1]" size={22} />
          <span className="ml-2 text-[#64748B] text-sm">Loading papers…</span>
        </div>
      ) : error ? (
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-12 text-center">
          <p className="text-[#94A3B8]">Error: {error}</p>
        </div>
      ) : papers.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-12 text-center">
          <Search size={32} className="text-[#CBD5E1] mx-auto mb-3" />
          <p className="text-[#94A3B8]">No papers match your search</p>
          <button type="button" onClick={() => { setQuery(''); setServerSearch(''); setPage(1); }} className="mt-2 text-sm text-[#6366F1] hover:underline">Clear search</button>
        </div>
      ) : (
        // Keep existing content visible while fetching — prevents height collapse & scroll-to-top
        <div className={`space-y-3 transition-opacity duration-150 ${fetching ? 'opacity-40 pointer-events-none' : 'opacity-100'}`}>
          {papers.map(p => <PaperCard key={p.id} paper={p} query={serverSearch} />)}
        </div>
      )}

      {!initialLoad && !error && total > 0 && (
        <div className="flex items-center justify-between gap-4 pt-1">
          <p className="text-[#94A3B8] text-xs tabular-nums whitespace-nowrap">
            {from}–{to} of <span className="text-[#64748B]" style={{ fontWeight: 500 }}>{total}</span>
          </p>

          <div className="flex items-center gap-1">
            <button type="button" onClick={() => goTo(page - 1)} disabled={page === 1}
              className="w-8 h-8 rounded-lg border border-[#E2E8F0] flex items-center justify-center text-[#94A3B8] hover:text-[#0F172A] hover:border-[#CBD5E1] disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              <ChevronLeft size={14} />
            </button>
            {pageNums[0] > 1 && <>{btnPage(1)}{pageNums[0] > 2 && <span className="text-[#CBD5E1] text-xs px-0.5">…</span>}</>}
            {pageNums.map(n => btnPage(n))}
            {pageNums[pageNums.length - 1] < totalPages && <>{pageNums[pageNums.length - 1] < totalPages - 1 && <span className="text-[#CBD5E1] text-xs px-0.5">…</span>}{btnPage(totalPages)}</>}
            <button type="button" onClick={() => goTo(page + 1)} disabled={page === totalPages}
              className="w-8 h-8 rounded-lg border border-[#E2E8F0] flex items-center justify-center text-[#94A3B8] hover:text-[#0F172A] hover:border-[#CBD5E1] disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              <ChevronRight size={14} />
            </button>
          </div>

          <div className="flex items-center gap-2 whitespace-nowrap">
            <span className="text-[#94A3B8] text-xs">Per page</span>
            <div className="flex items-center gap-1">
              {PAGE_SIZES.map(s => (
                <button key={s} type="button" onClick={() => { setPageSize(s); setPage(1); }}
                  className="px-2.5 py-1 rounded-lg border text-xs transition-all"
                  style={{ background: pageSize === s ? '#F1F5F9' : 'white', color: pageSize === s ? '#0F172A' : '#94A3B8', border: `1px solid ${pageSize === s ? '#CBD5E1' : '#E2E8F0'}`, fontWeight: pageSize === s ? 600 : 400 }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="flex items-start gap-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-3">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: '#B91C1C' }}>
          <span className="text-white text-xs" style={{ fontWeight: 700 }}>aX</span>
        </div>
        <p className="text-[#64748B] text-xs">
          Papers sourced from <strong>arXiv</strong> · Classified via hybrid RRF (dense cosine + BM25) · Stored in <strong>Pinecone</strong> (768-dim) · Run <code className="bg-gray-100 px-1 rounded">python run.py ingest</code> for new papers
        </p>
      </div>
    </div>
  );
}