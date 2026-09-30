import { LanguageOption } from '../types';

export const LANGUAGES: LanguageOption[] = [
  { code: 'en', label: 'English', nativeLabel: 'English', locale: 'en-IN' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिन्दी', locale: 'hi-IN' },
  { code: 'kn', label: 'Kannada', nativeLabel: 'ಕನ್ನಡ', locale: 'kn-IN' },
  { code: 'ta', label: 'Tamil', nativeLabel: 'தமிழ்', locale: 'ta-IN' },
  { code: 'te', label: 'Telugu', nativeLabel: 'తెలుగు', locale: 'te-IN' },
  { code: 'mr', label: 'Marathi', nativeLabel: 'मराठी', locale: 'mr-IN' },
  { code: 'bn', label: 'Bengali', nativeLabel: 'বাংলা', locale: 'bn-IN' },
];

export const DEFAULT_LANGUAGE_CODE = 'en';

export function isValidLanguageCode(code: string | null | undefined): code is LanguageOption['code'] {
  if (!code) return false;
  return LANGUAGES.some((lang) => lang.code === code);
}
