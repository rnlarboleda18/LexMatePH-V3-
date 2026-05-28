import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Star, Gavel, BookOpen, CreditCard, Loader2, AlertTriangle } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react';
import { apiUrl } from '../utils/apiUrl';
import { useFavorites } from '../hooks/useFavorites';
import { useBarQuestions } from '../hooks/useBarQuestions';
import { useFlashcardConcepts } from '../hooks/useFlashcardConcepts';
import { useSubscription } from '../context/SubscriptionContext';
import QuestionDetailModal from './QuestionDetailModal';
import Flashcard from './Flashcard';

const TABS = [
  { key: 'case', label: 'Cases', icon: Gavel },
  { key: 'bar_question', label: 'Bar Questions', icon: BookOpen },
  { key: 'flashcard', label: 'Flashcards', icon: CreditCard },
];

function FavoriteCard({ item, onClick, onRemove }) {
  const { isFavorited, toggleFavorite } = useFavorites(item.content_type, item.content_id);

  const handleRemove = useCallback(
    async (e) => {
      e.stopPropagation();
      const succeeded = await toggleFavorite();
      // Only remove from list if the API call succeeded;
      // toggleFavorite rolls back cache on failure so isFavorited stays true.
      if (succeeded) onRemove(item.content_id);
    },
    [toggleFavorite, onRemove, item.content_id]
  );

  return (
    <div
      className="group flex cursor-pointer items-start gap-3 rounded-xl border border-lex bg-white p-3 shadow-sm transition-all hover:border-yellow-300 hover:shadow-md dark:border-lex dark:bg-zinc-900 dark:hover:border-yellow-600"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
          {item.title || item.content_id}
        </p>
        {item.subtitle && (
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{item.subtitle}</p>
        )}
        {item.created_at && (
          <p className="mt-1 text-[10px] text-gray-400 dark:text-gray-500">
            Saved {new Date(item.created_at).toLocaleDateString('en-PH', { month: 'short', day: 'numeric', year: 'numeric' })}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={handleRemove}
        className="shrink-0 rounded-full border border-yellow-300/80 bg-yellow-50/90 p-1 text-yellow-500 transition-all hover:bg-red-50 hover:text-red-500 dark:border-yellow-600/60 dark:bg-yellow-900/40 dark:text-yellow-400 dark:hover:bg-red-900/40 dark:hover:text-red-400"
        title="Remove from favorites"
        aria-label="Remove from favorites"
      >
        <Star className="h-3.5 w-3.5" fill="currentColor" strokeWidth={2} />
      </button>
    </div>
  );
}

export default function Favorites({ onCaseSelect }) {
  const { getToken, isSignedIn } = useAuth();
  const { canAccess } = useSubscription();
  const [activeTab, setActiveTab] = useState('case');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [openQuestion, setOpenQuestion] = useState(null);
  const [openFlashcard, setOpenFlashcard] = useState(null);

  // Load data needed for modal re-open
  const { questions } = useBarQuestions({ enabled: activeTab === 'bar_question' || activeTab === 'flashcard' });
  const { conceptPool } = useFlashcardConcepts({ enabled: activeTab === 'flashcard' });

  const fetchItems = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');
      const r = await fetch(apiUrl(`/api/favorites?type=${activeTab}`), {
        headers: { 'X-Clerk-Authorization': `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setItems(data);
    } catch (err) {
      setError(err.message || 'Failed to load favorites');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken, activeTab]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const handleRemove = useCallback((contentId) => {
    setItems((prev) => prev.filter((i) => i.content_id !== contentId));
  }, []);

  const handleItemClick = useCallback(
    (item) => {
      if (item.content_type === 'case') {
        onCaseSelect?.({ id: item.content_id });
      } else if (item.content_type === 'bar_question') {
        const q = questions.find((q) => String(q.id) === String(item.content_id));
        if (q) {
          setOpenQuestion(q);
        } else {
          alert('Question data is still loading. Please try again in a moment.');
        }
      } else if (item.content_type === 'flashcard') {
        const isBar = /^\d+$/.test(item.content_id);
        if (isBar) {
          const q = questions.find((q) => String(q.id) === String(item.content_id));
          if (q) {
            setOpenFlashcard({ card: q, variant: 'bar' });
          } else {
            alert('Flashcard data is still loading. Please try again in a moment.');
          }
        } else {
          const c = conceptPool.find(
            (c) => encodeURIComponent(c.term || '') === item.content_id
          );
          if (c) {
            setOpenFlashcard({ card: c, variant: 'concepts' });
          } else {
            alert('Flashcard data is still loading. Please try again in a moment.');
          }
        }
      }
    },
    [onCaseSelect, questions, conceptPool]
  );

  if (!canAccess('favorites')) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8 text-center">
        <div>
          <Star className="mx-auto mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" />
          <p className="font-semibold text-gray-600 dark:text-gray-400">Favorites require an Amicus plan or higher.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto min-h-screen w-full max-w-4xl px-3 py-6 sm:px-5 lg:px-6">
      <div className="mb-6 flex items-center gap-3">
        <Star className="h-6 w-6 text-yellow-500" fill="currentColor" />
        <h1 className="text-2xl font-black tracking-tight text-gray-900 dark:text-gray-100">Favorites</h1>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-2 border-b border-lex pb-1">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-sm font-semibold transition-colors ${
              activeTab === key
                ? 'border-b-2 border-yellow-500 text-yellow-600 dark:text-yellow-400'
                : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading && (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
        </div>
      )}

      {error && !loading && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <AlertTriangle className="h-8 w-8 text-red-400" />
          <p className="text-sm text-red-500">{error}</p>
          <button
            type="button"
            onClick={fetchItems}
            className="rounded-lg border border-red-300 px-4 py-1.5 text-xs font-bold text-red-500 hover:bg-red-50"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <Star className="h-10 w-10 text-gray-300 dark:text-gray-600" />
          <p className="text-base font-semibold text-gray-500 dark:text-gray-400">No favorites yet</p>
          <p className="text-sm text-gray-400 dark:text-gray-500">Star items while browsing to save them here.</p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <FavoriteCard
              key={item.content_id}
              item={item}
              onClick={() => handleItemClick(item)}
              onRemove={handleRemove}
            />
          ))}
        </div>
      )}

      {/* Bar question modal */}
      {openQuestion && (
        <QuestionDetailModal
          question={openQuestion}
          onClose={() => setOpenQuestion(null)}
        />
      )}

      {/* Flashcard modal */}
      {openFlashcard &&
        createPortal(
          <div
            className="fixed inset-0 z-[540] flex items-center justify-center bg-black/40 backdrop-blur-md"
            onClick={() => setOpenFlashcard(null)}
          >
            <div
              className="relative flex max-w-5xl flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <Flashcard
                variant={openFlashcard.variant}
                card={openFlashcard.card}
                total={1}
                currentIndex={0}
                onClose={() => setOpenFlashcard(null)}
              />
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
