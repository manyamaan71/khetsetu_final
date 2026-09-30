export type Language = 'en' | 'hi';
export interface Bi<T = string> { en: T; hi: T }

/** The ML model's answer. Only present when confidence >= the backend threshold. */
export interface Prediction {
  class_name: string;
  crop: string;
  disease: string;
  confidence: number;
  is_healthy: boolean;
  crop_hi: string;
  disease_hi: string;
}

/** General agricultural advice from data/guidance.json. NOT produced by the model. */
export interface Guidance {
  class_name: string;
  crop: string;
  is_healthy: boolean;
  urgency: 'none' | 'act_soon' | 'act_fast';
  condition: Bi;
  what_is_it: Bi;
  symptoms: Bi<string[]>;
  possible_cause: Bi;
  prevention: Bi<string[]>;
  basic_care: Bi<string[]>;
  watering_care: Bi<string[]>;
  nutrient_guidance: Bi<string[]>;
  consult_expert_when: Bi<string[]>;
  avoid: Bi<string[]>;
  source_note: Bi;
}

interface ScanBase {
  client_scan_id?: string;
  demo_mode: boolean;
  confidence_threshold: number;
  model: { mode: string; format: string };
  timing_ms?: { preprocess: number; inference: number; total: number };
}

export interface ScanOk extends ScanBase {
  status: 'ok';
  is_confident: true;
  confidence: number;
  prediction: Prediction;
  guidance: Guidance;
  message: null;
  extra_explanation?: { text: string; language: Language; ai_generated: boolean };
}

export interface ScanRejected extends ScanBase {
  status: 'low_confidence' | 'not_a_leaf';
  is_confident: false;
  confidence: number | null;
  prediction: null;
  guidance: null;
  message: { title: Bi; body: Bi; tips: Bi<string[]> };
}

export type ScanApiResponse = ScanOk | ScanRejected;

export interface HistoryItem {
  id: string;
  date: string;
  crop: string;
  disease: string;
  hindi_crop: string;
  hindi_disease: string;
  confidence: number;
  is_healthy: boolean;
  is_confident: boolean;
  thumbnail?: string;
  result?: ScanOk;          // full result so "View" works offline
}

export interface MarketPriceRow {
  market: string; crop: string; state: string; district: string;
  min_price: number; max_price: number; modal_price: number; date: string; unit: string;
}

export interface MarketResponse {
  rows: MarketPriceRow[];
  is_demo: boolean;
  source: 'live' | 'cached' | 'demo' | 'unavailable';
  stale: boolean;
  fetched_at: string;
  message: Bi | null;
}

export interface MarketQuery { crop?: string; state?: string; district?: string }

export interface HealthInfo {
  status: string;
  demo_mode: boolean;
  model: { mode: 'real' | 'demo' | 'unavailable'; format: string };
  confidence_threshold: number;
  market_data: string;
}
