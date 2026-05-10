import { Helmet } from 'react-helmet-async';

const BASE_URL = 'https://lexmateph.com';
const DEFAULT_IMAGE = `${BASE_URL}/pwa-512x512.png`;

/**
 * Per-route SEO metadata definitions.
 * Keys match the MODE_TO_PATH values in App.jsx.
 */
const ROUTE_META = {
  about: {
    path: '/',
    title: 'LexMatePH · Your Philippine Law Companion',
    description:
      'LexMatePH — the all-in-one Philippine bar review app. SC decisions, case digests, codals, bar questions, flashcards, and LexPlay audio review. Free to explore.',
  },
  supreme_decisions: {
    path: '/decisions',
    title: 'SC Case Digests · LexMatePH',
    description:
      'High-fidelity, comprehensive Supreme Court of the Philippines case digests. Search by GR number, ponente, division, or keyword. Updated regularly.',
  },
  codex: {
    path: '/lexcode',
    title: 'Philippine Codals · LexMatePH',
    description:
      'Full text of the Revised Penal Code, Civil Code, Family Code, Rules of Court, Labor Code, and more — with linked jurisprudence.',
  },
  browse_bar: {
    path: '/bar-questions',
    title: 'Bar Exam Questions · LexMatePH',
    description:
      'Philippine bar exam questions from past years. Filter by subject: Civil Law, Criminal Law, Political Law, Remedial Law, Commercial Law, and more.',
  },
  flashcard: {
    path: '/flashcards',
    title: 'Legal Concept Flashcards · LexMatePH',
    description:
      'Study key Philippine legal concepts with smart flashcards. Covers all bar subjects with AI-generated digests for faster retention.',
  },
  lexplay: {
    path: '/lexplay',
    title: 'LexPlay Audio Review · LexMatePH',
    description:
      'Listen to Philippine codals, case digests, and bar questions with LexPlay — the audio review feature of LexMatePH. Study on the go.',
  },
  updates: {
    path: '/updates',
    title: 'Updates · LexMatePH',
    description:
      'Latest updates, new features, and improvements to LexMatePH — your Philippine law companion.',
  },
  legal: {
    path: '/legal',
    title: 'Legal & Privacy · LexMatePH',
    description:
      'Terms of Service, Privacy Policy, and legal information for LexMatePH.',
  },
  quiz: {
    path: '/lexify',
    title: 'Lexify Exam Simulator · LexMatePH',
    description:
      'Practice with actual Philippine bar exam questions and suggested answers. AI-powered checking grounded on official suggested answers — know exactly where you stand.',
  },
  lexmate: {
    path: '/lexmate',
    title: 'LexMate AI · LexMatePH',
    description:
      'Ask legal questions and get AI-powered answers grounded in Philippine law with LexMate.',
  },
};

/**
 * Drop-in SEO head component. Place at the top of each page/route.
 *
 * @param {object} props
 * @param {string} props.mode - App mode key (matches ROUTE_META keys above)
 * @param {string} [props.title] - Override title
 * @param {string} [props.description] - Override description
 * @param {string} [props.image] - Override OG image URL
 */
export default function SeoHead({ mode, title, description, image }) {
  const meta = ROUTE_META[mode] || ROUTE_META.about;
  const resolvedTitle = title || meta.title;
  const resolvedDesc = description || meta.description;
  const resolvedImage = image || DEFAULT_IMAGE;
  const canonicalUrl = `${BASE_URL}${meta.path}`;

  return (
    <Helmet>
      {/* Primary */}
      <title>{resolvedTitle}</title>
      <meta name="description" content={resolvedDesc} />
      <link rel="canonical" href={canonicalUrl} />

      {/* Open Graph (Facebook, LinkedIn, WhatsApp, etc.) */}
      <meta property="og:type" content="website" />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:title" content={resolvedTitle} />
      <meta property="og:description" content={resolvedDesc} />
      <meta property="og:image" content={resolvedImage} />
      <meta property="og:site_name" content="LexMatePH" />
      <meta property="og:locale" content="en_PH" />

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={resolvedTitle} />
      <meta name="twitter:description" content={resolvedDesc} />
      <meta name="twitter:image" content={resolvedImage} />
    </Helmet>
  );
}
