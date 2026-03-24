/**
 * Native IndexedDB Wrapper for LexMatePH v3
 * Zero-dependency caching layer using Stale-While-Revalidate pattern.
 *
 * IMPORTANT: IndexedDB stores objects. Arrays must be wrapped in a container
 * before storing, otherwise the spread operator ({ ...arr }) converts them
 * into plain objects with numeric keys, breaking .map() calls on retrieval.
 */

const DB_NAME = 'LexMateCacheDB';
const DB_VERSION = 1;

class LexCache {
  constructor() {
    this.db = null;
    this.initPromise = this.init();
  }

  async init() {
    if (typeof window === 'undefined' || typeof indexedDB === 'undefined') return null;
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains('cases')) {
          db.createObjectStore('cases', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('codals')) {
          db.createObjectStore('codals', { keyPath: 'key' });
        }
        if (!db.objectStoreNames.contains('questions')) {
          db.createObjectStore('questions', { keyPath: 'id' });
        }
      };

      request.onsuccess = (event) => {
        this.db = event.target.result;
        resolve(this.db);
      };

      request.onerror = (event) => reject(event.target.error);
    });
  }

  async get(storeName, id) {
    const db = await this.initPromise;
    if (!db) return null;
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.get(id);
      request.onsuccess = () => {
        const record = request.result;
        if (!record) return resolve(null);
        // Unwrap arrays that were stored in a container
        if (record._isArray && Array.isArray(record._data)) {
          return resolve(record._data);
        }
        resolve(record);
      };
      request.onerror = () => reject(request.error);
    });
  }

  async set(storeName, key, data) {
    const db = await this.initPromise;
    if (!db) return;
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);

      let record;
      if (Array.isArray(data)) {
        // Wrap arrays to prevent spread-to-object corruption
        record = { key, _isArray: true, _data: data, _cachedAt: Date.now() };
      } else {
        record = { ...data, key, _cachedAt: Date.now() };
        // Ensure primary key is set for non-codal stores
        if (storeName === 'cases' && !record.id) record.id = key;
        if (storeName === 'questions' && !record.id) record.id = key;
      }

      const request = store.put(record);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Stale-While-Revalidate fetch wrapper.
   * @param {string} storeName - 'cases', 'codals', or 'questions'
   * @param {string|number} id - Unique cache key
   * @param {function} fetcher - Async function that fetches fresh data from API
   * @param {function} onUpdate - Callback called with (data, isCached). May be called twice.
   */
  async swr(storeName, id, fetcher, onUpdate) {
    // 1. Serve from cache immediately if available
    let cached = null;
    try {
      cached = await this.get(storeName, id);
    } catch (e) {
      console.warn(`LexCache: Failed to read from cache (${storeName}/${id}):`, e);
    }

    if (cached !== null && onUpdate) {
      onUpdate(cached, true);
    }

    // 2. Revalidate in background
    try {
      const fresh = await fetcher();
      if (fresh !== undefined && fresh !== null) {
        // Compare (ignore cache metadata)
        const cachedStr = cached !== null ? JSON.stringify(cached) : null;
        const freshStr = JSON.stringify(fresh);

        if (cachedStr !== freshStr) {
          await this.set(storeName, id, fresh);
          if (onUpdate) onUpdate(fresh, false);
        }
      }
    } catch (error) {
      console.error(`LexCache: SWR revalidation failed for ${storeName}/${id}:`, error);
      // If we had no cache and fetch failed, propagate
      if (cached === null) throw error;
    }

    return cached;
  }
}

export const lexCache = new LexCache();
