import React, { useState } from 'react';

export default function CitationCard({ citation, index }) {
  const [expanded, setExpanded] = useState(false);

  const isCase   = citation.type === 'case';
  const verified = citation.verified;

  return (
    <div
      className={`rounded-lg border p-3 text-sm cursor-pointer transition-colors ${
        verified
          ? 'border-green-200 bg-green-50 hover:bg-green-100'
          : 'border-yellow-200 bg-yellow-50 hover:bg-yellow-100'
      }`}
      onClick={() => setExpanded(e => !e)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
            verified ? 'bg-green-500 text-white' : 'bg-yellow-500 text-white'
          }`}>
            {index + 1}
          </span>
          <div className="min-w-0">
            {isCase ? (
              <>
                <p className="font-medium text-gray-900 truncate">
                  {citation.case_name}
                </p>
                <p className="text-gray-500 text-xs">
                  G.R. No. {citation.gr_number} · {citation.date}
                </p>
              </>
            ) : (
              <>
                <p className="font-medium text-gray-900 truncate">
                  {citation.law_name}
                </p>
                <p className="text-gray-500 text-xs">{citation.provision}</p>
              </>
            )}
          </div>
        </div>
        <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded ${
          verified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
        }`}>
          {verified ? 'verified' : 'unverified'}
        </span>
      </div>

      {expanded && (
        <p className="mt-2 pt-2 border-t border-current/10 text-gray-600 font-mono text-xs break-all">
          {citation.raw}
        </p>
      )}
    </div>
  );
}
