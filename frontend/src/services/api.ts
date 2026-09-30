import { ScanApiResponse, MarketResponse, MarketQuery, HealthInfo, Language } from '../types';

// Dev: Vite proxies /api to FastAPI (vite.config.ts). Production: set VITE_API_BASE_URL.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export type ApiErrorCode =
  | 'network' | 'timeout' | 'server' | 'invalid_image' | 'too_large' | 'model_unavailable' | 'offline';

export class ApiError extends Error {
  code: ApiErrorCode;
  constructor(code: ApiErrorCode, message: string) {
    super(message);
    this.code = code;
  }
}

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;       // backend limit (applies AFTER compression)
const MAX_ORIGINAL_BYTES = 25 * 1024 * 1024;           // phone photos are big; we compress them first
export const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const REQUEST_TIMEOUT_MS = 30_000;

export function validateImageType(file: File): void {
  if (!ALLOWED_TYPES.includes(file.type)) throw new ApiError('invalid_image', 'Unsupported file type');
  if (file.size > MAX_ORIGINAL_BYTES) throw new ApiError('too_large', 'File is far too large');
}

/** Resize + re-encode as JPEG so uploads are small and fast on slow networks. */
export async function compressImage(file: File, maxDimension = 1024, quality = 0.82): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width, height } = img;
      if (width > maxDimension || height > maxDimension) {
        const scale = maxDimension / Math.max(width, height);
        width = Math.round(width * scale);
        height = Math.round(height * scale);
      }
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) return reject(new Error('Canvas not supported'));
      ctx.drawImage(img, 0, 0, width, height);
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Compression failed'))), 'image/jpeg', quality);
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Invalid image')); };
    img.src = url;
  });
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) throw new ApiError('offline', 'Offline');
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(`${API_BASE}${path}`, { ...init, signal: ctrl.signal });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw new ApiError('timeout', 'Request timed out');
    throw new ApiError('network', 'Network request failed');
  } finally {
    clearTimeout(timer);
  }
}

async function errorFrom(res: Response): Promise<ApiError> {
  let code = '';
  try { code = (await res.json())?.detail?.code ?? ''; } catch { /* not JSON */ }
  if (res.status === 413 || code === 'image_too_large') return new ApiError('too_large', 'File too large');
  if (res.status === 422 || code === 'invalid_image' || code === 'bad_request' || code === 'empty_file')
    return new ApiError('invalid_image', 'Invalid image');
  if (res.status === 503 || code === 'model_unavailable') return new ApiError('model_unavailable', 'Model unavailable');
  return new ApiError('server', 'Server error');
}

export async function predictCrop(file: File, language: 'en' | 'hi'): Promise<ScanApiResponse> {
  validateImageType(file);
  let payload: Blob = file;
  try { payload = await compressImage(file); } catch { /* fall back to the original file */ }
  if (payload.size > MAX_UPLOAD_BYTES) throw new ApiError('too_large', 'File exceeds 5MB limit');

  const form = new FormData();
  form.append('image', payload, 'leaf.jpg');
  form.append('language', language);
  const res = await request('/predict', { method: 'POST', body: form });
  if (!res.ok) throw await errorFrom(res);
  return res.json();
}

export async function downloadScanReport(image: Blob, language: Language): Promise<{ blob: Blob; filename: string }> {
  const form = new FormData();
  form.append('image', image, 'scan.jpg');
  form.append('language', language);
  const res = await request('/report/pdf', { method: 'POST', body: form });
  if (!res.ok) throw await errorFrom(res);
  const disposition = res.headers.get('content-disposition') || '';
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || 'KhetSetu_Report.pdf';
  return { blob: await res.blob(), filename };
}

export async function fetchMarketPrices(query: MarketQuery): Promise<MarketResponse> {
  const params = new URLSearchParams();
  if (query.crop) params.set('crop', query.crop);
  if (query.state) params.set('state', query.state);
  if (query.district) params.set('district', query.district);
  const res = await request(`/market-prices?${params.toString()}`);
  if (!res.ok) throw new ApiError('server', 'Server error');
  return res.json();
}

export async function fetchHealth(): Promise<HealthInfo | null> {
  try {
    const res = await request('/health');
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}
