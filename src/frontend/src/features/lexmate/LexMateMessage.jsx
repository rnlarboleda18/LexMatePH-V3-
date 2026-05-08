import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CitationCard from './CitationCard';

function UserMessage({ content }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
        {content}
      </div>
    </div>
  );
}

// Walk ReactMarkdown children and highlight [citation] marks in string nodes
function highlightCitations(children) {
  return React.Children.map(children, (child, i) => {
    if (typeof child !== 'string') return child;
    const parts = child.split(/(\[[^\]]+\])/g);
    if (parts.length === 1) return child;
    return parts.map((part, j) =>
      part.startsWith('[') && part.endsWith(']')
        ? <mark key={`${i}-${j}`} className="bg-indigo-50 text-indigo-700 rounded px-0.5 not-italic font-medium">{part}</mark>
        : <React.Fragment key={`${i}-${j}`}>{part}</React.Fragment>
    );
  });
}

const MD_COMPONENTS = {
  p:      ({ children }) => <p className="mb-2 last:mb-0">{highlightCitations(children)}</p>,
  strong: ({ children }) => <strong className="font-semibold text-gray-900">{highlightCitations(children)}</strong>,
  em:     ({ children }) => <em className="italic">{highlightCitations(children)}</em>,
  ul:     ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-0.5">{children}</ul>,
  ol:     ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-0.5">{children}</ol>,
  li:     ({ children }) => <li className="text-sm">{highlightCitations(children)}</li>,
  h1:     ({ children }) => <h1 className="font-bold text-base mb-1 mt-2">{children}</h1>,
  h2:     ({ children }) => <h2 className="font-semibold text-sm mb-1 mt-2">{children}</h2>,
  h3:     ({ children }) => <h3 className="font-medium text-sm mb-1 mt-1">{children}</h3>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-indigo-200 pl-3 italic text-gray-600 mb-2">{children}</blockquote>
  ),
  code:   ({ inline, children }) => inline
    ? <code className="bg-gray-100 text-gray-800 rounded px-1 text-xs font-mono">{children}</code>
    : <pre className="bg-gray-50 border border-gray-200 rounded p-2 text-xs font-mono overflow-x-auto mb-2"><code>{children}</code></pre>,
};

function AssistantMessage({ message }) {
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied]           = useState(false);
  const hasCitations = message.citations?.length > 0;
  const hasSources   = message.sources?.length > 0;

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  };

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-3">
        {/* Answer bubble */}
        <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">
              L
            </div>
            <span className="text-xs font-medium text-gray-500">LexMate</span>
            {message.cached && (
              <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">cached</span>
            )}
            {message.modelUsed && (
              <span className="text-xs text-gray-400">{message.modelUsed.includes('pro') ? '⚡ Pro' : '⚡ Flash'}</span>
            )}
            <button
              onClick={handleCopy}
              className="ml-auto text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-100 transition-colors"
              title="Copy answer"
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>

          <div className="text-sm text-gray-800 leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
              {message.content}
            </ReactMarkdown>
          </div>

          {message.warning && (
            <p className="mt-2 text-xs text-yellow-600 bg-yellow-50 rounded px-2 py-1">
              ⚠ {message.warning === 'no_context'
                  ? 'The legal corpus is currently indexing — retrieval will improve as more documents are embedded.'
                  : message.warning}
            </p>
          )}
        </div>

        {/* Citations */}
        {hasCitations && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide px-1">
              Citations ({message.citations.length})
            </p>
            {message.citations.map((c, i) => (
              <CitationCard key={i} citation={c} index={i} />
            ))}
          </div>
        )}

        {/* Sources toggle */}
        {hasSources && (
          <button
            onClick={() => setShowSources(s => !s)}
            className="text-xs text-indigo-500 hover:text-indigo-700 px-1"
          >
            {showSources ? '▲ Hide' : '▼ Show'} {message.sources.length} source{message.sources.length !== 1 ? 's' : ''}
          </button>
        )}

        {showSources && hasSources && (
          <div className="space-y-1">
            {message.sources.map((s, i) => (
              <div key={i} className="text-xs bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 flex items-center justify-between">
                <div>
                  <span className="font-medium text-gray-700">{s.title || s.gr_number || `Source ${i + 1}`}</span>
                  {s.gr_number && <span className="text-gray-400 ml-2">· G.R. {s.gr_number}</span>}
                  {s.date && <span className="text-gray-400 ml-2">· {s.date}</span>}
                </div>
                {s.score > 0 && (
                  <span className="text-gray-400 ml-2 tabular-nums">{(s.score * 100).toFixed(0)}%</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function LexMateMessage({ message }) {
  if (message.role === 'user') {
    return <UserMessage content={message.content} />;
  }
  return <AssistantMessage message={message} />;
}
