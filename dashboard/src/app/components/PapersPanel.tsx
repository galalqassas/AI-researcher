import { useState, useMemo, useEffect } from 'react';
import { Search, Filter, ExternalLink, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { fetchPapers, BUCKET_CONFIG, type BucketKey, type Paper } from '../data/api';

const ALL_BUCKET_KEYS = Object.keys(BUCKET_CONFIG) as BucketKey[];

function highlightMatch(text: string, query: string) {
  if (!query.trim()) return text;
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  const parts = text.split(regex);
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} style={{ background: '#FEF9C3', color: '#0F172A', borderRadius: '2px', padding: '0 1px' }}>{part}</mark>
    ) : part
  );
}

function PaperCard({ paper, query }: { paper: Paper; query: string }) {
  const [expanded, setExpanded] = useState(false);
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
            <h4 className="text-[#0F172A]" style={{ fontWeight: 600 }}>{highlightMatch(paper.title, query)}</h4>
            <a
              href={`https://arxiv.org/abs/${paper.arxiv_id}`}
              target="_blank" rel="noopener noreferrer"
              className="flex-shrink-0 w-7 h-7 rounded-lg border border-[#E2E8F0] flex items-center justify-center text-[#94A3B8] hover:text-[#6366F1] hover:border-[#6366F1] transition-colors"
            >
              <ExternalLink size={13} />
            </a>
          </div>
          <p className="text-[#94A3B8] text-xs mt-1">
            {paper.authors || 'Unknown authors'} · {paper.published_date || '—'} · <span className="font-mono">arXiv:{paper.arxiv_id}</span>
          </p>
          <div className="flex items-center gap-1.5 mt-2 flex-wrap">
            {paper.buckets.map(b => (
              <span key={b} className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: BUCKET_CONFIG[b].colorLight, color: BUCKET_CONFIG[b].color, fontWeight: 600, border: `1px solid ${BUCKET_CONFIG[b].color}25` }}>
                {BUCKET_CONFIG[b].label}
              </span>
            ))}
          </div>
          {paper.abstract && (
            <div className="mt-3">
              <p className={`text-[#475569] text-sm ${expanded ? '' : 'line-clamp-2'}`}>
                {highlightMatch(paper.abstract, query)}
              </p>
              <button onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs mt-1.5 text-[#6366F1] hover:text-[#4F46E5] transition-colors"
                style={{ fontWeight: 600 }}>
                {expanded ? <><ChevronUp size={12} /> Show less</> : <><ChevronDown size={12} /> Read more</>}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface PapersPanelProps {
  onPapersLoaded?: (count: number) => void;
}

export function PapersPanel({ onPapersLoaded }: PapersPanelProps) {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [activeBucket, setActiveBucket] = useState<BucketKey | 'all'>('all');

  const filtered = useMemo(() => {
    let result = papers;
    if (query.trim()) {
      const q = query.toLowerCase();
      result = result.filter(p =>
        p.title.toLowerCase().includes(q) ||
        (p.abstract || '').toLowerCase().includes(q) ||
        (p.authors || '').toLowerCase().includes(q) ||
        p.arxiv_id.toLowerCase().includes(q)
      );
    }
    return result;
  }, [papers, query]);

  useEffect(() => {
    setLoading(true);
    fetchPapers(activeBucket === 'all' ? undefined : activeBucket, 1, 200)
      .then(data => {
        setPapers(data.results);
        setTotalCount(data.total);
        if (onPapersLoaded) onPapersLoaded(data.total);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeBucket]);

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
            placeholder="Filter by title, abstract, author…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[#E2E8F0] bg-white text-sm text-[#0F172A] placeholder:text-[#CBD5E1] focus:outline-none focus:ring-2 focus:ring-[#6366F1]/30 focus:border-[#6366F1] transition-all" />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <button onClick={() => setActiveBucket('all')}
            className="px-3 py-2 rounded-xl text-sm transition-all"
            style={{ background: activeBucket === 'all' ? '#0F172A' : 'white', color: activeBucket === 'all' ? 'white' : '#64748B', border: `1px solid ${activeBucket === 'all' ? '#0F172A' : '#E2E8F0'}`, fontWeight: activeBucket === 'all' ? 600 : 400 }}>
            All ({totalCount})
          </button>
          {ALL_BUCKET_KEYS.map(key => {
            const cfg = BUCKET_CONFIG[key];
            const count = papers.filter(p => p.buckets.includes(key)).length;
            const active = activeBucket === key;
            return (
              <button key={key} onClick={() => setActiveBucket(key)}
                className="px-3 py-2 rounded-xl text-sm transition-all flex items-center gap-1.5"
                style={{ background: active ? cfg.colorLight : 'white', color: active ? cfg.color : '#64748B', border: `1px solid ${active ? cfg.color + '50' : '#E2E8F0'}`, fontWeight: active ? 600 : 400 }}>
                <div className="w-2 h-2 rounded-full" style={{ background: cfg.color }} />
                {cfg.label} ({count})
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-[#64748B] text-sm">
          {filtered.length === papers.length ? `Showing all ${filtered.length} papers` : `${filtered.length} paper${filtered.length !== 1 ? 's' : ''} found`}
          {query && <span className="ml-1">for "<strong className="text-[#0F172A]">{query}</strong>"</span>}
        </p>
        {(query || activeBucket !== 'all') && (
          <button onClick={() => { setQuery(''); setActiveBucket('all'); }} className="text-xs text-[#6366F1] hover:underline" style={{ fontWeight: 600 }}>Clear filters</button>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin text-[#6366F1]" size={24} /><span className="ml-2 text-[#64748B]">Loading papers…</span></div>
      ) : error ? (
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-12 text-center"><p className="text-[#94A3B8]">Error: {error}</p></div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-[#E2E8F0] p-12 text-center">
          <Search size={32} className="text-[#CBD5E1] mx-auto mb-3" />
          <p className="text-[#94A3B8]">No papers match your search</p>
          <button onClick={() => { setQuery(''); setActiveBucket('all'); }} className="mt-2 text-sm text-[#6366F1] hover:underline">Clear filters</button>
        </div>
      ) : (
        <div className="space-y-3">{filtered.map(paper => <PaperCard key={paper.id} paper={paper} query={query} />)}</div>
      )}

      <div className="flex items-start gap-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl px-4 py-3">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: '#B91C1C' }}>
          <span className="text-white text-xs" style={{ fontWeight: 700 }}>aX</span>
        </div>
        <p className="text-[#64748B] text-xs">
          Papers sourced from <strong>arXiv</strong> · Classified via hybrid RRF (dense cosine + BM25) · Stored in <strong>Qdrant</strong> (768-dim) · Run <code className="bg-gray-100 px-1 rounded">python run.py ingest</code> for new papers
        </p>
      </div>
    </div>
  );
}