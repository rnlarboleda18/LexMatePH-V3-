import { useState, useEffect, useCallback } from 'react';
import { apiUrl } from '../utils/apiUrl';

/**
 * Hook to fetch and hierarchically structure bar reviewer topics for a subject.
 * Pass isAdmin=true to include draft topics (requires admin auth).
 */
export function useTopics(subject, { isAdmin = false } = {}) {
  const [topics, setTopics] = useState([]);
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTopics = useCallback(() => {
    if (!subject) {
      setTopics([]);
      setTree([]);
      return;
    }

    setLoading(true);
    setError(null);

    const url = isAdmin
      ? apiUrl(`/api/reviewer/${subject}?all=true`)
      : apiUrl(`/api/reviewer/${subject}`);
    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error(`Failed to fetch topics: ${r.statusText}`);
        return r.json();
      })
      .then(data => {
        const flatTopics = data.topics || [];
        setTopics(flatTopics);
        setTree(buildTopicTree(flatTopics));
        setLoading(false);
      })
      .catch(err => {
        console.error('useTopics error:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [subject, isAdmin]);

  useEffect(() => {
    fetchTopics();
  }, [fetchTopics]);

  return { topics, tree, loading, error, refresh: fetchTopics };
}

/**
 * Transforms a flat list of topics into a nested tree.
 * When parent_path is null (new path format), groups by roman_num automatically.
 */
function buildTopicTree(flatTopics) {
  const map = {};
  const roots = [];

  flatTopics.forEach(t => {
    map[t.topic_path] = { ...t, children: [] };
  });

  // Check if any topic has a resolvable parent_path
  const hasExplicitParents = flatTopics.some(
    t => t.parent_path && map[t.parent_path]
  );

  if (hasExplicitParents) {
    // Original behaviour: use parent_path links
    flatTopics.forEach(t => {
      const node = map[t.topic_path];
      if (t.parent_path && map[t.parent_path]) {
        map[t.parent_path].children.push(node);
      } else {
        roots.push(node);
      }
    });
  } else {
    // New path format (parent_path is null): group by roman_num
    const sections = {};
    const sectionOrder = [];

    flatTopics.forEach(t => {
      if (!sections[t.roman_num]) {
        const virtualPath = `__section__${t.roman_num}`;
        sections[t.roman_num] = {
          topic_path: virtualPath,
          roman_num: t.roman_num,
          topic_heading: t.topic_heading,
          sub_letter: null,
          id: null,
          status: null,
          sort_order: t.sort_order,
          children: [],
        };
        sectionOrder.push(t.roman_num);
        roots.push(sections[t.roman_num]);
      }
      sections[t.roman_num].children.push(map[t.topic_path]);
    });
  }

  const sortRecursive = (nodes) => {
    nodes.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    nodes.forEach(n => { if (n.children.length > 0) sortRecursive(n.children); });
  };

  sortRecursive(roots);
  return roots;
}
