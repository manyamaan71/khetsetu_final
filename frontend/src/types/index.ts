export type Language = 'en' | 'hi' | 'kn' | 'ta' | 'te' | 'mr' | 'bn';
export type PreferredLanguage = Language | (string & {});

export interface LanguageOption {
  code: Language;
  label: string;
  nativeLabel: string;
  locale: string;
}

export interface Bi<T = string> { en: T; hi: T; [key: string]: T }

export interface FarmerProfile {
  id?: string;
  user_id: string;
  full_name: string;
  phone?: string | null;
  preferred_language: PreferredLanguage;
  state: string | null;
  district: string | null;
  taluk: string | null;
  village: string | null;
  crops: string[] | null;
  farm_size: string | number | null;
  onboarding_completed?: boolean;
  created_at?: string;
  updated_at?: string;
}

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

/** Disease-specific advisory returned by the backend. This is the authoritative object for the result page. */
export interface Advisory {
  class_name: string;
  crop: string;
  disease: string;
  is_healthy: boolean;
  urgency: 'none' | 'act_soon' | 'act_fast';
  what_we_found: Bi;
  why_it_happened: Bi<string[]>;
  symptoms: Bi<string[]>;
  risk_factors: Bi<string[]>;
  immediate_actions: Bi<string[]>;
  management: Bi<string[]>;
  prevention: Bi<string[]>;
  avoid: Bi<string[]>;
  when_to_seek_help: Bi<string[]>;
  severity: Bi;
  spread_risk: Bi;
  source_note: Bi;
  condition?: Bi;
  what_is_it?: Bi;
  possible_cause?: Bi;
  basic_care?: Bi<string[]>;
  watering_care?: Bi<string[]>;
  nutrient_guidance?: Bi<string[]>;
  consult_expert_when?: Bi<string[]>;
}

/** Legacy guidance object kept for compatibility with older screens and tests. */
export type Guidance = Advisory;

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
  advisory?: Guidance;
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
