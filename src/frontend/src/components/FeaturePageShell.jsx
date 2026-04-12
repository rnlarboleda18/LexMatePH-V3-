import React from 'react';

/**
 * Shared chrome for feature areas (Flashcards, About, Updates, etc.):
 * max-w-7xl main, no secondary header.
 */
const FeaturePageShell = ({ children }) => {
  return (
    <div className="min-h-screen bg-transparent font-sans text-gray-900 dark:text-gray-100">
      <main className="mx-auto max-w-7xl px-3 py-4 sm:px-5 sm:py-5 lg:px-6">{children}</main>
    </div>
  );
};

export default React.memo(FeaturePageShell);
