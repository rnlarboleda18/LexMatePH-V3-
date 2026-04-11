import React from 'react';
import { Lock, Zap, Star, Shield, Crown } from 'lucide-react';
import { useSubscription } from '../context/SubscriptionContext';

const TIER_INFO = {
  amicus: {
    icon: <Zap className="w-6 h-6" />,
    color: 'from-blue-500 to-indigo-600',
    textColor: 'text-blue-600 dark:text-blue-400',
    borderColor: 'border-blue-200 dark:border-blue-800',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    price: '₱199/mo',
  },
  juris: {
    icon: <Star className="w-6 h-6" />,
    color: 'from-purple-500 to-violet-600',
    textColor: 'text-purple-600 dark:text-purple-400',
    borderColor: 'border-purple-200 dark:border-purple-800',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    price: '₱499/mo',
  },
  barrister: {
    icon: <Crown className="w-6 h-6" />,
    color: 'from-amber-500 to-orange-600',
    textColor: 'text-amber-600 dark:text-amber-400',
    borderColor: 'border-amber-200 dark:border-amber-800',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    price: '₱999/mo',
  },
};

const FEATURE_COPY = {
  case_digest_unlimited: {
    title: 'Unlimited Case Digests',
    description: "You've reached your 5 free case digests for today.",
    benefit: 'Get unlimited access to all Supreme Court case digests.',
  },
  bar_question_unlimited: {
    title: 'Unlimited Bar Questions',
    description: "You've reached your 5 free bar question views for today.",
    benefit: 'View unlimited Bar Exam questions and suggested answers.',
  },
  flashcard_unlimited: {
    title: 'Unlimited Flashcards',
    description: "You've used your 5 free flashcards for today.",
    benefit: 'Practice with unlimited flashcards across all subjects.',
  },
  case_digest_download_unlimited: {
    title: 'Unlimited Case Digest Downloads',
    description: "You've reached your 5 free case digest downloads for today.",
    benefit: 'Download unlimited case digests as PDF for offline study.',
  },
  codex_linked_cases: {
    title: 'LexCode Jurisprudence + Case Digests',
    description: 'Viewing linked jurisprudence and case digests in LexCode requires a Juris subscription.',
    benefit: 'See which Supreme Court cases apply to each codal provision, and read their full digests inline.',
  },
  lexplay_unlimited: {
    title: 'Unlimited Codal LexPlay',
    description: "You've reached your daily Codal LexPlay limit.",
    benefit: 'Listen to codal provisions without any daily time limit.',
  },
  lexplay_flashcard: {
    title: 'LexPlay — Flashcards',
    description: 'Audio playback for Flashcards requires a Juris subscription.',
    benefit: 'Listen to legal concept terms, definitions, and bar question flashcards read aloud.',
  },
  lexplay_bar: {
    title: 'LexPlay — Bar Questions',
    description: 'Audio playback for Bar Questions requires a Barrister subscription.',
    benefit: 'Listen to Bar Exam questions and suggested answers read aloud.',
  },
  lexplay_case_digest: {
    title: 'LexPlay — Case Digests',
    description: 'Audio playback for Case Digests requires a Barrister subscription.',
    benefit: 'Listen to Supreme Court case digests read aloud.',
  },
  download_tracks: {
    title: 'Download Tracks to Device',
    description: 'Downloading audio tracks for offline use requires a Juris subscription.',
    benefit: 'Save any LexPlay track to your device for offline listening.',
  },
  lexify: {
    title: 'Lexify Bar Simulator',
    description: 'Lexify is exclusively available to Barrister subscribers.',
    benefit: 'Simulate the actual Bar Exam with AI-powered essay grading.',
  },
};

/**
 * UpgradeWall — inline or modal upgrade prompt.
 * Props:
 *   feature: string (key from FEATURE_COPY / FEATURE_REQUIREMENTS)
 *   variant: 'inline' | 'modal' | 'compact'
 *   onClose: optional — for modal variant
 */
export default function UpgradeWall({ feature, variant = 'inline', onClose }) {
  const { openUpgradeModal, FEATURE_REQUIREMENTS, TIER_LABELS } = useSubscription();

  const requiredTier = FEATURE_REQUIREMENTS[feature] || 'amicus';
  const info = TIER_INFO[requiredTier] || TIER_INFO.amicus;
  const copy = FEATURE_COPY[feature] || {
    title: 'Premium Feature',
    description: 'This feature requires a paid subscription.',
    benefit: 'Upgrade to unlock this feature.',
  };

  if (variant === 'compact') {
    return (
      <div
        className={`flex items-center gap-3 p-3 rounded-xl border ${info.borderColor} ${info.bgColor} cursor-pointer hover:opacity-90 transition-opacity`}
        onClick={() => openUpgradeModal(feature)}
      >
        <div className={`p-1.5 rounded-lg bg-gradient-to-br ${info.color} text-white`}>
          <Lock className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-xs font-bold ${info.textColor}`}>{copy.title}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{info.price} · {TIER_LABELS[requiredTier]} Plan</p>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); openUpgradeModal(feature); }}
          className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-gradient-to-r ${info.color} shadow-sm`}
        >
          Upgrade
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      {/* Lock icon with gradient */}
      <div className={`mb-6 relative`}>
        <div className={`w-20 h-20 rounded-full bg-gradient-to-br ${info.color} flex items-center justify-center shadow-lg`}>
          <Lock className="w-8 h-8 text-white" />
        </div>
        <div className={`absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center border-2 ${info.borderColor} ${info.textColor}`}>
          {info.icon}
        </div>
      </div>

      {/* Title and Description */}
      <h3 className="text-xl font-extrabold text-gray-900 dark:text-white mb-2">{copy.title}</h3>
      <p className="text-gray-500 dark:text-gray-400 text-sm mb-2 max-w-sm">{copy.description}</p>
      <p className="text-gray-700 dark:text-gray-300 text-sm font-medium max-w-sm mb-8">{copy.benefit}</p>

      {/* Required Tier Badge */}
      <div className={`mb-6 px-4 py-2 rounded-full border ${info.borderColor} ${info.bgColor} ${info.textColor} text-sm font-bold flex items-center gap-2`}>
        {info.icon}
        Requires {TIER_LABELS[requiredTier]} Plan — {info.price}
      </div>

      {/* CTA */}
      <button
        onClick={() => openUpgradeModal(feature)}
        className={`px-8 py-3.5 rounded-xl text-white font-extrabold text-sm bg-gradient-to-r ${info.color} shadow-lg hover:opacity-90 active:scale-95 transition-all`}
      >
        Upgrade to {TIER_LABELS[requiredTier]}
      </button>

      {variant === 'modal' && onClose && (
        <button
          onClick={onClose}
          className="mt-4 text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
        >
          Maybe later
        </button>
      )}
    </div>
  );
}
