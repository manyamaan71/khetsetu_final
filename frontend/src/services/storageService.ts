import { HistoryItem } from '../types';

const HISTORY_KEY = 'khetsetu_history';
const LAST_RESULT_KEY = 'khetsetu_last_result';
const MAX_HISTORY_ITEMS = 50;
const SCAN_DB_NAME = 'khetsetu_scan';
const SCAN_STORE_NAME = 'current';

function openScanDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SCAN_DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(SCAN_STORE_NAME);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveCurrentScanImage(scanId: string, image: Blob): Promise<void> {
  const db = await openScanDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(SCAN_STORE_NAME, 'readwrite');
    const store = transaction.objectStore(SCAN_STORE_NAME);
    store.clear();
    store.put({ scanId, image }, 'latest');
    transaction.oncomplete = () => { db.close(); resolve(); };
    transaction.onerror = () => { db.close(); reject(transaction.error); };
    transaction.onabort = () => { db.close(); reject(transaction.error); };
  });
}

export async function getCurrentScanImage(scanId: string): Promise<Blob | null> {
  const db = await openScanDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(SCAN_STORE_NAME, 'readonly');
    const request = transaction.objectStore(SCAN_STORE_NAME).get('latest');
    request.onsuccess = () => {
      db.close();
      const record = request.result as { scanId: string; image: Blob } | undefined;
      resolve(record?.scanId === scanId ? record.image : null);
    };
    request.onerror = () => { db.close(); reject(request.error); };
  });
}

export function getHistory(): HistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? (JSON.parse(raw) as HistoryItem[]) : [];
  } catch {
    return [];
  }
}

export function addHistoryItem(item: HistoryItem): void {
  const history = getHistory();
  history.unshift(item);
  const trimmed = history.slice(0, MAX_HISTORY_ITEMS);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
  } catch {
    // storage full or unavailable - fail silently, history is a convenience feature
  }
}

export function clearHistory(): void {
  try { localStorage.removeItem(HISTORY_KEY); } catch { /* ignore */ }
}

export function saveLastResult(data: unknown): void {
  try {
    localStorage.setItem(LAST_RESULT_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
}

export function getLastResult<T>(): T | null {
  try {
    const raw = localStorage.getItem(LAST_RESULT_KEY);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

/** Downscale an image to a small thumbnail data-URL for lightweight local storage. */
export function makeThumbnail(file: File, size = 96): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      if (!ctx) return reject(new Error('no canvas'));
      const scale = Math.max(size / img.width, size / img.height);
      const w = img.width * scale;
      const h = img.height * scale;
      ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);
      resolve(canvas.toDataURL('image/jpeg', 0.6));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('invalid image'));
    };
    img.src = url;
  });
}
