import { Component, type ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC] p-6">
          <div className="bg-white rounded-2xl border border-[#E2E8F0] p-8 max-w-md w-full text-center shadow-sm">
            <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-100 flex items-center justify-center mx-auto mb-4">
              <AlertCircle size={22} className="text-rose-500" />
            </div>
            <h2 className="text-[#0F172A] text-lg mb-2" style={{ fontWeight: 600 }}>Something went wrong</h2>
            <p className="text-[#94A3B8] text-sm mb-6">
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-white transition-all hover:opacity-90"
              style={{ background: 'linear-gradient(145deg, #818CF8, #6366F1)' }}
            >
              <RefreshCw size={14} />
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
