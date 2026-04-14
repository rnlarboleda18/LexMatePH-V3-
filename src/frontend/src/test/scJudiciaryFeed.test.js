import { describe, it, expect } from 'vitest';
import { buildUnifiedFeed, isBarRelatedPost, parseFeedDateMs } from '../utils/scJudiciaryFeed';

describe('isBarRelatedPost', () => {
  it('detects bar bulletin in title', () => {
    expect(isBarRelatedPost({ title: 'Bar Bulletin No. 3', categories: [] })).toBe(true);
  });
  it('returns false for unrelated news', () => {
    expect(isBarRelatedPost({ title: 'Court holiday schedule', categories: ['News'] })).toBe(false);
  });
});

describe('parseFeedDateMs', () => {
  it('parses RFC-style pubDate', () => {
    const ms = parseFeedDateMs('Wed, 09 Mar 2026 12:00:00 +0000');
    expect(ms).toBeGreaterThan(0);
  });
});

describe('buildUnifiedFeed', () => {
  it('dedupes by link and merges bar highlight', () => {
    const items = [
      { title: 'A', link: 'https://x/a', pub_date: 'Wed, 01 Jan 2026 00:00:00 +0000', categories: [] },
    ];
    const barItems = [
      {
        title: 'Bar Bulletin A',
        link: 'https://x/a',
        pub_date: 'Wed, 01 Jan 2026 00:00:00 +0000',
        categories: [],
      },
      {
        title: 'Bar exam notice',
        link: 'https://x/b',
        pub_date: 'Thu, 02 Jan 2026 00:00:00 +0000',
        categories: [],
      },
    ];
    const u = buildUnifiedFeed(items, barItems);
    expect(u).toHaveLength(2);
    const a = u.find((x) => x.link.endsWith('/a'));
    expect(a._barHighlight).toBe(true);
    const b = u.find((x) => x.link.endsWith('/b'));
    expect(b._barHighlight).toBe(true);
  });

  it('sorts by pubDate descending', () => {
    const items = [
      { title: 'Old', link: 'https://x/1', pub_date: 'Mon, 01 Jan 2024 00:00:00 +0000', categories: [] },
      { title: 'New', link: 'https://x/2', pub_date: 'Tue, 02 Jan 2026 00:00:00 +0000', categories: [] },
    ];
    const u = buildUnifiedFeed(items, []);
    expect(u[0].title).toBe('New');
  });
});
