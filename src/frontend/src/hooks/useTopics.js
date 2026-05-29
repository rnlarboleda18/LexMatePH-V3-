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
 * Transforms a flat list of topics with topic_path and parent_path 
 * into a nested tree structure.
 */
function buildTopicTree(flatTopics) {
  const map = {};
  const roots = [];

  // Initialize map
  flatTopics.forEach(t => {
    map[t.topic_path] = { ...t, children: [] };
  });

  // Build tree
  flatTopics.forEach(t => {
    const node = map[t.topic_path];
    if (t.parent_path && map[t.parent_path]) {
      map[t.parent_path].children.push(node);
    } else {
      // It's a root (Roman numeral level or similar)
      roots.push(node);
    }
  });

  // Sort children by sort_order
  const sortRecursive = (nodes) => {
    nodes.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    nodes.forEach(n => {
      if (n.children.length > 0) {
        sortRecursive(n.children);
      }
    });
  };

  sortRecursive(roots);
  return roots;
}
