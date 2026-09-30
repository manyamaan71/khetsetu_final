/**
 * speechService.ts - text-to-speech.
 *
 * Default provider: the browser's Web Speech API (free, works offline if the phone has a
 * Hindi voice installed). Hindi uses lang "hi-IN".
 *
 * Later upgrade (e.g. Sarvam): implement `TtsProvider` by calling YOUR backend
 * (POST /api/speech -> audio) and register it with `setTtsProvider()`. The API key must stay
 * on the server (backend/app/services/sarvam_service.py) - never in this frontend.
 */
export type SpeechLang = 'hi-IN' | 'en-IN';

export interface TtsProvider {
  isSupported(): boolean;
  speak(text: string, lang: SpeechLang): Promise<void>;
  stop(): void;
  isSpeaking(): boolean;
  hasVoiceFor(lang: SpeechLang): boolean;
}

function voices(): SpeechSynthesisVoice[] {
  return typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis.getVoices() : [];
}

/** Chrome stops long utterances after ~15 s, so speak sentence-sized chunks one after another. */
function chunk(text: string, max = 180): string[] {
  const parts = text.replace(/\s+/g, ' ').split(/(?<=[.!?।])\s+/);
  const out: string[] = [];
  let cur = '';
  for (const p of parts) {
    if ((cur + ' ' + p).trim().length > max && cur) { out.push(cur.trim()); cur = p; }
    else cur = (cur + ' ' + p).trim();
  }
  if (cur) out.push(cur);
  return out;
}

let cancelled = false;

const browserProvider: TtsProvider = {
  isSupported: () => typeof window !== 'undefined' && 'speechSynthesis' in window,
  hasVoiceFor: (lang) => voices().some((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase())),
  isSpeaking: () => browserProvider.isSupported() && window.speechSynthesis.speaking,
  stop: () => { cancelled = true; if (browserProvider.isSupported()) window.speechSynthesis.cancel(); },
  speak: (text, lang) =>
    new Promise<void>((resolve) => {
      if (!browserProvider.isSupported() || !text) return resolve();
      window.speechSynthesis.cancel();
      cancelled = false;
      const queue = chunk(text);
      const voice = voices().find((v) => v.lang === lang) || voices().find((v) => v.lang.startsWith(lang.slice(0, 2)));
      const next = () => {
        const part = queue.shift();
        if (!part || cancelled) return resolve();
        const u = new SpeechSynthesisUtterance(part);
        u.lang = lang;
        u.rate = 0.92;
        if (voice) u.voice = voice;
        u.onend = next;
        u.onerror = () => resolve();
        window.speechSynthesis.speak(u);
      };
      next();
    }),
};

let provider: TtsProvider = browserProvider;
export function setTtsProvider(p: TtsProvider) { provider = p; }

export const isSpeechSupported = () => provider.isSupported();
export const hasVoiceFor = (lang: SpeechLang) => provider.hasVoiceFor(lang);
export const speak = (text: string, lang: SpeechLang = 'hi-IN') => provider.speak(text, lang);
export const stopSpeaking = () => provider.stop();
export const isSpeaking = () => provider.isSpeaking();

// Voices load asynchronously in Chrome/Android; touching the list early makes them available by the time the user taps.
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.getVoices(); };
}
