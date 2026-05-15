import { Helmet } from 'react-helmet-async';

const BASE_URL = 'https://www.lexmateph.com';
const DEFAULT_IMAGE = `${BASE_URL}/pwa-512x512.png`;

/**
 * Per-route SEO metadata definitions.
 * Keys match the MODE_TO_PATH values in App.jsx.
 */
const ROUTE_META = {
  about: {
    path: '/',
    title: 'LexMatePH - Your all-in-one Legal Companion App. One App does all.',
    description:
      'LexMatePH — the all-in-one Philippine bar review app. SC decisions, case digests, codals, bar questions, flashcards, and LexPlay audio review. Free to explore.',
    keywords:
      'LexMatePH, Philippine bar exam, bar review app, Philippine law, law companion, bar reviewer Philippines',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'EducationalApplication',
      name: 'LexMatePH',
      url: BASE_URL,
      description:
        'The all-in-one Philippine bar review app — SC decisions, case digests, codals, bar questions, flashcards, and LexPlay audio review.',
      applicationCategory: 'EducationApplication',
      operatingSystem: 'Web, iOS, Android (PWA)',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'PHP' },
      author: { '@type': 'Organization', name: 'LexMatePH' },
      inLanguage: 'en-PH',
    },
  },
  supreme_decisions: {
    path: '/decisions',
    title: 'SC Case Digests · LexMatePH',
    description:
      'High-fidelity, comprehensive Supreme Court of the Philippines case digests. Search by GR number, ponente, division, or keyword. Updated regularly.',
    keywords:
      'Supreme Court Philippines case digest, SC decisions Philippines, GR number search, Philippine jurisprudence, Philippine case law',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'DataCatalog',
      name: 'Supreme Court of the Philippines Case Digests',
      description:
        'High-fidelity, comprehensive Supreme Court of the Philippines case digests searchable by GR number, ponente, division, or keyword.',
      url: `${BASE_URL}/decisions`,
      publisher: { '@type': 'Organization', name: 'LexMatePH', url: BASE_URL },
      inLanguage: 'en-PH',
      about: { '@type': 'Thing', name: 'Philippine Jurisprudence' },
    },
  },
  codex: {
    path: '/lexcode',
    title: 'Philippine Codals · LexMatePH',
    description:
      'Full text of the Revised Penal Code, Civil Code, Family Code, Rules of Court, Labor Code, and more — with linked jurisprudence.',
    keywords:
      'Revised Penal Code Philippines, Civil Code Philippines, Family Code Philippines, Rules of Court Philippines, Labor Code Philippines, Philippine codals full text',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'LegalDocument',
      name: 'Philippine Codals — Full Text',
      description:
        'Full text of major Philippine laws including the Revised Penal Code, Civil Code, Family Code, Rules of Court, and Labor Code.',
      url: `${BASE_URL}/lexcode`,
      inLanguage: 'en-PH',
      publisher: { '@type': 'Organization', name: 'LexMatePH', url: BASE_URL },
    },
  },
  browse_bar: {
    path: '/bar-questions',
    title: 'Bar Exam Questions · LexMatePH',
    description:
      'Philippine bar exam questions from past years. Filter by subject: Civil Law, Criminal Law, Political Law, Remedial Law, Commercial Law, and more.',
    keywords:
      'Philippine bar exam questions, bar exam reviewer, bar questions Civil Law, bar questions Criminal Law, bar questions Political Law, bar questions Remedial Law, Philippine bar 2024 2025',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'Quiz',
      name: 'Philippine Bar Exam Questions',
      description:
        'Philippine bar exam questions from past years, filterable by subject including Civil Law, Criminal Law, Political Law, Remedial Law, and Commercial Law.',
      url: `${BASE_URL}/bar-questions`,
      educationalLevel: 'Professional',
      about: { '@type': 'Thing', name: 'Philippine Bar Examination' },
      publisher: { '@type': 'Organization', name: 'LexMatePH', url: BASE_URL },
      inLanguage: 'en-PH',
    },
  },
  flashcard: {
    path: '/flashcards',
    title: 'Legal Concept Flashcards · LexMatePH',
    description:
      'Study key Philippine legal concepts with smart flashcards. Covers all bar subjects with AI-generated digests for faster retention.',
    keywords:
      'Philippine law flashcards, bar exam flashcards, legal concepts Philippines, bar review flashcards, law school Philippines',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'Course',
      name: 'Philippine Legal Concept Flashcards',
      description:
        'Smart flashcards covering key Philippine legal concepts for all bar subjects, powered by AI-generated digests.',
      url: `${BASE_URL}/flashcards`,
      provider: { '@type': 'Organization', name: 'LexMatePH', url: BASE_URL },
      educationalLevel: 'Professional',
      inLanguage: 'en-PH',
    },
  },
  lexplay: {
    path: '/lexplay',
    title: 'LexPlay Audio Review · LexMatePH',
    description:
      'Listen to Philippine codals, case digests, and bar questions with LexPlay — the audio review feature of LexMatePH. Study on the go.',
    keywords:
      'Philippine law audio review, bar exam audio, law podcast Philippines, LexPlay, codal audio Philippines',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'AudioObject',
      name: 'LexPlay — Philippine Law Audio Review',
      description:
        'Audio review of Philippine codals, case digests, and bar questions. Study Philippine law on the go.',
      url: `${BASE_URL}/lexplay`,
      publisher: { '@type': 'Organization', name: 'LexMatePH', url: BASE_URL },
      inLanguage: 'en-PH',
    },
  },
  quiz: {
    path: '/lexify',
    title: 'Lexify Exam Simulator · LexMatePH',
    description:
      'Practice with actual Philippine bar exam questions and suggested answers. AI-powered checking grounded on official suggested answers — know exactly where you stand.',
    keywords:
      'bar exam simulator Philippines, bar exam practice, Philippine bar questions suggested answers, AI bar review, bar exam checker Philippines',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'Quiz',
      name: 'Lexify — Philippine Bar Exam Simulator',
      description:
        'Practice Philippine bar exam questions with AI-powered checking grounded on official suggested answers.',
      url: `${BASE_URL}/lexify`,
      educationalLevel: 'Professional',
      about: { '@type': 'Thing', name: 'Philippine Bar Examination' },
      publisher: { '@type': 'Organization', name: 'LexMatePH', url: BASE_URL },
      inLanguage: 'en-PH',
    },
  },
  lexmate: {
    path: '/lexmate',
    title: 'LexMate AI · LexMatePH',
    description:
      'Ask legal questions and get AI-powered answers grounded in Philippine law with LexMate.',
    keywords:
      'Philippine law AI, legal assistant Philippines, AI lawyer Philippines, LexMate, ask Philippine law',
    schema: {
      '@context': 'https://schema.org',
      '@type': 'SoftwareApplication',
      name: 'LexMate AI Legal Assistant',
      description:
        'AI-powered legal assistant grounded in Philippine law. Ask questions and get accurate, sourced answers.',
      url: `${BASE_URL}/lexmate`,
      applicationCategory: 'EducationApplication',
      operatingSystem: 'Web',
      publisher: { '@type': 'Organization', name: 'LexMatePH', url: BASE_URL },
      inLanguage: 'en-PH',
    },
  },
  updates: {
    path: '/updates',
    title: 'Updates · LexMatePH',
    description:
      'Latest updates, new features, and improvements to LexMatePH - Your all-in-one Legal Companion App. One App does all.',
    keywords: 'LexMatePH updates, LexMatePH new features, Philippine law app updates',
    schema: null,
  },
  legal: {
    path: '/legal',
    title: 'Legal & Privacy · LexMatePH',
    description: 'Terms of Service, Privacy Policy, and legal information for LexMatePH.',
    keywords: 'LexMatePH terms of service, LexMatePH privacy policy',
    schema: null,
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
      <meta name="keywords" content={meta.keywords} />
      <meta name="author" content="LexMatePH" />
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

      {/* JSON-LD Structured Data */}
      {meta.schema && (
        <script type="application/ld+json">
          {JSON.stringify(meta.schema)}
        </script>
      )}
    </Helmet>
  );
}
