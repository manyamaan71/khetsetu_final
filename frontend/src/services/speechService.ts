/**
 * speechService.ts - text-to-speech.
 *
 * Uses the optional Sarvam backend first and keeps Web Speech as the offline/unavailable fallback.
 */
import { LANGUAGES, DEFAULT_LANGUAGE_CODE } from '../config/languages';
import { requestTtsAudio, TtsHttpError } from './api';

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

/** Keep chunks short enough for the TTS API and split long sentences at word boundaries. */
function chunk(text: string, max = 450): string[] {
  const parts = text.replace(/\s+/g, ' ').trim().split(/(?<=[.!?।])\s*/).filter(Boolean);
  const out: string[] = [];
  let cur = '';
  for (const p of parts) {
    const sentence = p.trim();
    if (!sentence) continue;
    if (sentence.length > max) {
      if (cur) { out.push(cur); cur = ''; }
      let remaining = sentence;
      while (remaining.length > max) {
        let boundary = remaining.lastIndexOf(' ', max);
        if (boundary <= 0) boundary = max;
        out.push(remaining.slice(0, boundary).trim());
        remaining = remaining.slice(boundary).trim();
      }
      cur = remaining;
    } else if ((cur + ' ' + sentence).trim().length > max && cur) {
      out.push(cur);
      cur = sentence;
    } else {
      cur = (cur + ' ' + sentence).trim();
    }
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
      const queue = chunk(text, 180);
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
const audioCache = new Map<string, Blob>();

export function setTtsProvider(p: TtsProvider) { provider = p; }

interface AudioChunk {
  text: string;
  splitRetried: boolean;
}

type ChunkAudioResult = { audio: Blob | null; splitForLengthError: boolean };

function isLengthError(error: TtsHttpError): boolean {
  return error.status === 413
    || (error.status === 400 && /length|too long|maximum|characters|payload/i.test(error.responseBody));
}

function splitChunkInHalf(text: string): [string, string] | null {
  const middle = Math.floor(text.length / 2);
  let boundary = text.lastIndexOf(' ', middle);
  if (boundary <= 0) boundary = text.indexOf(' ', middle);
  if (boundary <= 0 || boundary >= text.length - 1) {
    const characters = Array.from(text);
    const splitAt = Math.floor(characters.length / 2);
    const first = characters.slice(0, splitAt).join('');
    const second = characters.slice(splitAt).join('');
    return first && second ? [first, second] : null;
  }
  const first = text.slice(0, boundary).trim();
  const second = text.slice(boundary + 1).trim();
  return first && second ? [first, second] : null;
}

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

  const chunks = chunk(text);
  if (typeof navigator === 'undefined' || navigator.onLine) {
    const queue: AudioChunk[] = chunks.map((part) => ({ text: part, splitRetried: false }));
    const fetchAudio = async (part: string): Promise<ChunkAudioResult> => {
      const key = JSON.stringify([lang, part]);
      const cached = audioCache.get(key);
      if (cached) return { audio: cached, splitForLengthError: false };
      try {
        const response = await requestTtsAudio(part, lang);
        if (response) audioCache.set(key, response);
        return { audio: response, splitForLengthError: false };
      } catch (error) {
        return {
          audio: null,
          splitForLengthError: error instanceof TtsHttpError && isLengthError(error),
        };
      }
    };

    let pendingAudio = queue.length ? fetchAudio(queue[0].text) : Promise.resolve(null);
    for (let index = 0; index < queue.length; index += 1) {
      const currentChunk = queue[index];
      const audioResult = await pendingAudio;
      if (generation !== speechGeneration || cancelled) return false;
      if (audioResult === null) return false;
      if (audioResult.splitForLengthError && !currentChunk.splitRetried) {
        const halves = splitChunkInHalf(currentChunk.text);
        if (halves) {
          queue.splice(
            index,
            1,
            { text: halves[0], splitRetried: true },
            { text: halves[1], splitRetried: true },
          );
          pendingAudio = fetchAudio(queue[index].text);
          index -= 1;
          continue;
        }
      }
      if (!audioResult.audio) {
        if (!browserProvider.hasVoiceFor(lang)) return false;
        await browserProvider.speak(queue.slice(index).map((part) => part.text).join(' '), lang);
        return true;
      }

      const nextAudio = index + 1 < queue.length ? fetchAudio(queue[index + 1].text) : null;
      if (!await playAudioBlob(audioResult.audio, generation)) {
        if (generation !== speechGeneration || cancelled || !browserProvider.hasVoiceFor(lang)) return false;
        await browserProvider.speak(queue.slice(index).map((part) => part.text).join(' '), lang);
        return true;
      }
      if (nextAudio) pendingAudio = nextAudio;
    }
    if (queue.length) return true;
  }

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
