/**
 * Native IndexedDB Wrapper for LexMatePH v3
 * zero-dependency caching layer for legal texts.
 */

const DB_NAME = 'LexMateCacheDB';
const DB_VERSION = 1;

class LexCache {
  constructor() {
    this.db = null;
    this.initPromise = this.init();
  }

  async init() {
    if (typeof window === 'undefined') return null;
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        // Store for case digests
        if (!db.objectStoreNames.contains('cases')) {
          db.createObjectStore('cases', { keyPath: 'id' });
        }
        // Store for codal articles
        if (!db.objectStoreNames.contains('codals')) {
          db.createObjectStore('codals', { keyPath: 'key' }); // key = `${code}_${article_num}`
        }
        // Store for bar questions
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
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async set(storeName, data) {
    const db = await this.initPromise;
    if (!db) return;
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.put({
        ...data,
        _cachedAt: Date.now()
      });
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * SWR Fetch Wrapper
   * @param {string} storeName - 'cases', 'codals', or 'questions'
   * @param {string|number} id - Unique identifier for the item
   * @param {function} fetcher - Async function to fetch fresh data from API
   * @param {function} onUpdate - Callback for when fresh data is received (freshData, isCached)
   */
  async swr(storeName, id, fetcher, onUpdate) {
    // 1. Check Cache
    const cached = await this.get(storeName, id);
    
    // 2. If cached, call onUpdate immediately
    if (cached && onUpdate) {
      onUpdate(cached, true); 
    }

    // 3. Revalidate in background
    try {
      const fresh = await fetcher();
      if (fresh) {
        // Prepare comparison (remove cache metadata)
        const cachedComp = cached ? JSON.stringify({ ...cached, _cachedAt: undefined }) : null;
        const freshComp = JSON.stringify({ ...fresh, _cachedAt: undefined });
        
        if (cachedComp !== freshComp) {
          // Normalize ID for storage
          const dataToStore = { ...fresh };
          if (storeName === 'codals' && !dataToStore.key) dataToStore.key = id;
          if (storeName !== 'codals' && !dataToStore.id) dataToStore.id = id;

          await this.set(storeName, dataToStore);
          if (onUpdate) onUpdate(fresh, false);
        }
      }
    } catch (error) {
      console.error(`SWR revalidation failed for ${storeName}/${id}:`, error);
    }

    return cached;
  }
}

export const lexCache = new LexCache();
