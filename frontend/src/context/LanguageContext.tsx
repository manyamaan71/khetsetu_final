import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { Language, LanguageOption } from '../types';
import { translations, TranslationKey } from '../data/translations';
import { LANGUAGES, DEFAULT_LANGUAGE_CODE, isValidLanguageCode } from '../config/languages';
import { useAuth } from './AuthContext';

interface LanguageContextValue {
  language: Language;
  currentLanguage: Language;
  setLanguage: (lang: Language) => Promise<void>;
  availableLanguages: LanguageOption[];
  t: (key: TranslationKey) => string;
  isSavingLanguage: boolean;
  saveError: TranslationKey | null;
}

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined);
const LANGUAGE_STORAGE_KEY = 'khetsetu_language';

function readStoredLanguage(): Language | null {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return isValidLanguageCode(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { profile, isAuthenticated, loading, updateProfile } = useAuth();
  const [language, setLanguageState] = useState<Language>(() => readStoredLanguage() ?? DEFAULT_LANGUAGE_CODE);
  const [isSavingLanguage, setIsSavingLanguage] = useState(false);
  const [saveError, setSaveError] = useState<TranslationKey | null>(null);

  useEffect(() => {
    if (loading) return;
    const storedLanguage = readStoredLanguage();
    if (isAuthenticated && isValidLanguageCode(profile?.preferred_language)) {
      setLanguageState(storedLanguage ?? profile.preferred_language);
    } else if (!isAuthenticated) {
      setLanguageState(storedLanguage ?? DEFAULT_LANGUAGE_CODE);
    }
  }, [isAuthenticated, loading, profile?.preferred_language]);

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // Keep the in-memory preference when browser storage is unavailable.
    }
  }, [language]);

  const setLanguage = useCallback(
  async (nextLang: Language) => {
    const validLang = isValidLanguageCode(nextLang) ? nextLang : DEFAULT_LANGUAGE_CODE;
    setLanguageState(validLang);
    document.documentElement.lang = validLang;
    setSaveError(null);

    if (!isAuthenticated || !profile || profile.preferred_language === validLang) return;

    setIsSavingLanguage(true);
    try {
      await updateProfile({ preferred_language: validLang });
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('Could not persist preferred_language to Supabase (check SQL constraint):', err);
      }
      // Silently catch error so UI stays active in selected language without displaying error banner
    } finally {
      setIsSavingLanguage(false);
    }
  },
  [isAuthenticated, profile?.preferred_language, updateProfile]
);

  const t = useCallback(
    (key: TranslationKey): string => {
      const entry = translations[key] as Record<string, string> | undefined;
      if (!entry) return key as string;
      const localized = entry[language];
      if (localized) return localized;
      return '—';
    },
    [language]
  );

  return (
    <LanguageContext.Provider
      value={{
        language,
        currentLanguage: language,
        setLanguage,
        availableLanguages: LANGUAGES,
        t,
        isSavingLanguage,
        saveError,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
