/**
 * speechService.ts - text-to-speech.
 *
 * Uses the optional Sarvam backend first and keeps Web Speech as the offline/unavailable fallback.
 */
import { LANGUAGES, DEFAULT_LANGUAGE_CODE } from '../config/languages';
import { requestTtsAudio } from './api';

export type SpeechLang = string;

export function getSpeechLang(lang: string): SpeechLang {
  return LANGUAGES.find((item) => item.code === lang)?.locale
    ?? LANGUAGES.find((item) => item.code === DEFAULT_LANGUAGE_CODE)!.locale;
}

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
      const voice = voices().find((v) => v.lang === lang) || voices().find((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase()));
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
let activeSarvamAudio: HTMLAudioElement | null = null;
let activeSarvamUrl: string | null = null;
let cancelSarvamPlayback: (() => void) | null = null;
let speechGeneration = 0;

export function setTtsProvider(p: TtsProvider) { provider = p; }

async function playAudioBlob(response: Blob, generation: number): Promise<boolean> {
  let audioUrl: string | null = null;
  let cancelPlayback: (() => void) | null = null;
  try {
    audioUrl = URL.createObjectURL(response);
    const audio = new Audio(audioUrl);
    let resolvePlayback: ((played: boolean) => void) | undefined;
    const playback = new Promise<boolean>((resolve) => { resolvePlayback = resolve; });
    cancelPlayback = () => resolvePlayback?.(false);
    activeSarvamAudio = audio;
    activeSarvamUrl = audioUrl;
    cancelSarvamPlayback = cancelPlayback;
    audio.onended = () => resolvePlayback?.(true);
    audio.onerror = () => resolvePlayback?.(false);

    await audio.play();
    if (generation !== speechGeneration || cancelled) cancelPlayback();
    return await playback;
  } catch {
    return false;
  } finally {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    if (activeSarvamUrl === audioUrl) {
      activeSarvamAudio = null;
      activeSarvamUrl = null;
      if (cancelSarvamPlayback === cancelPlayback) cancelSarvamPlayback = null;
    }
  }
}

export const isSpeechSupported = () => provider.isSupported()
  || (typeof navigator !== 'undefined' && navigator.onLine);
export const hasVoiceFor = (lang: SpeechLang) => provider.hasVoiceFor(lang);

export async function speak(text: string, lang: SpeechLang = 'en-IN'): Promise<boolean> {
  stopSpeaking();
  const generation = ++speechGeneration;
  cancelled = false;

  if (provider !== browserProvider) {
    await provider.speak(text, lang);
    return true;
  }

  if (typeof navigator === 'undefined' || navigator.onLine) {
    const audioResponse = await requestTtsAudio(text, lang);
    if (audioResponse && generation === speechGeneration && !cancelled
      && await playAudioBlob(audioResponse, generation)) return true;
  }

  if (lang !== 'en-IN' && lang !== 'hi-IN') return false;
  if (generation !== speechGeneration || cancelled || !browserProvider.isSupported()) return false;
  if (!browserProvider.hasVoiceFor(lang)) return false;
  await browserProvider.speak(text, lang);
  return true;
}

export function stopSpeaking() {
  speechGeneration += 1;
  cancelled = true;
  cancelSarvamPlayback?.();
  activeSarvamAudio?.pause();
  activeSarvamAudio = null;
  if (activeSarvamUrl) URL.revokeObjectURL(activeSarvamUrl);
  activeSarvamUrl = null;
  provider.stop();
}

export const isSpeaking = () => Boolean(activeSarvamAudio && !activeSarvamAudio.paused) || provider.isSpeaking();

// Voices load asynchronously in Chrome/Android; touching the list early makes them available by the time the user taps.
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.getVoices(); };
}
