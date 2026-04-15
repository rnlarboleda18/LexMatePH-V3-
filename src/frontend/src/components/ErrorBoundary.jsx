import React from 'react';
import { RefreshCcw, AlertTriangle } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    // Optional: Clear problematic state if necessary
    // localStorage.removeItem('lexplay-state'); 
    this.setState({ hasError: false, error: null });
    window.location.reload(); // Hard reload to clear any corrupted context
  };

  handleHardReset = () => {
    if (window.confirm("This will clear your local settings and cache. Continue?")) {
      localStorage.clear();
      if ('caches' in window) {
        caches.keys().then(names => {
          for (let name of names) caches.delete(name);
        });
      }
      this.handleReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[300px] flex-col items-center justify-center space-y-6 rounded-[32px] border border-lex-strong bg-zinc-900 p-8 text-center animate-in fade-in zoom-in duration-300">
          <div className="w-20 h-20 bg-rose-500/20 rounded-full flex items-center justify-center text-rose-500 shadow-[0_0_30px_rgba(244,63,94,0.3)]">
            <AlertTriangle size={40} />
          </div>
          <div>
            <h2 className="text-2xl font-black text-white mb-2 tracking-tight">Something went wrong</h2>
            <p className="text-sm text-white/40 font-medium max-w-xs mx-auto">
              {this.props.message || "LexMate encountered an unexpected error while rendering this component."}
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-3">
             <button
                onClick={this.handleReset}
                className="px-8 py-3 bg-white text-slate-900 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-white/90 transition-all flex items-center gap-2"
              >
                <RefreshCcw size={16} />
                Refresh Page
              </button>
              <button
                onClick={this.handleHardReset}
                className="rounded-2xl border border-lex-strong bg-zinc-800 px-8 py-3 font-black text-xs uppercase tracking-widest text-zinc-400 transition-all hover:bg-zinc-700 hover:text-zinc-200"
              >
                Hard Reset
              </button>
          </div>

          {process.env.NODE_ENV === 'development' && (
            <details className="text-left w-full max-w-md bg-black/40 p-4 rounded-xl overflow-auto max-h-40">
              <summary className="text-[10px] text-white/20 uppercase font-black cursor-pointer hover:text-white/40 transition-colors">Technical Details</summary>
              <pre className="text-[10px] text-rose-300/60 mt-2 font-mono leading-relaxed">
                {this.state.error?.toString()}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
