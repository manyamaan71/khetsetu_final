import React from 'react';
import { Globe, Check } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { Language } from '../types';

interface LanguageSelectorProps {
  variant?: 'dropdown' | 'compact' | 'buttons';
  value?: Language;
  onChange?: (lang: Language) => void;
  className?: string;
  showLabel?: boolean;
}

export default function LanguageSelector({
  variant = 'dropdown',
  value,
  onChange,
  className = '',
  showLabel = false,
}: LanguageSelectorProps) {
  const { currentLanguage, setLanguage, availableLanguages, isSavingLanguage, saveError, t } = useLanguage();
  const activeLang = value ?? currentLanguage;

  const handleChange = (newLang: Language) => {
    if (onChange) {
      onChange(newLang);
    } else {
      void setLanguage(newLang);
    }
  };

  if (variant === 'buttons') {
    return (
      <div className={`grid grid-cols-2 sm:grid-cols-4 gap-2.5 ${className}`}>
        {availableLanguages.map((lang) => {
          const isSelected = activeLang === lang.code;
          return (
            <button
              key={lang.code}
              type="button"
              onClick={() => handleChange(lang.code)}
              className={`flex items-center justify-between px-3.5 py-3 rounded-2xl border text-left transition-all ${
                isSelected
                  ? 'border-leaf-600 bg-leaf-600 text-white shadow-sm font-bold'
                  : 'border-leaf-200 bg-leaf-50/60 hover:bg-leaf-100/50 text-gray-800 font-semibold'
              }`}
            >
              <div className="flex flex-col">
                <span className="text-base leading-tight">{lang.nativeLabel}</span>
                <span className={`text-xs ${isSelected ? 'text-leaf-100' : 'text-gray-500'}`}>{lang.label}</span>
              </div>
              {isSelected && <Check size={18} className="shrink-0 text-white" />}
            </button>
          );
        })}
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={`relative inline-flex flex-col items-start ${className}`}>
        <div className="flex items-center gap-1.5 bg-white border border-leaf-200 rounded-full px-3 py-1.5 shadow-sm hover:border-leaf-400 transition-colors">
          <Globe size={16} className="text-leaf-600 shrink-0" />
          <select
            value={activeLang}
            disabled={isSavingLanguage}
            onChange={(e) => handleChange(e.target.value as Language)}
            className="bg-transparent text-sm font-semibold text-leaf-900 outline-none cursor-pointer pr-1"
            aria-label={t('choose_language')}
          >
            {availableLanguages.map((lang) => (
              <option key={lang.code} value={lang.code} className="text-gray-900 bg-white font-medium py-1">
                {lang.nativeLabel} ({lang.label})
              </option>
            ))}
          </select>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-1.5 ${className}`}>
      {showLabel && (
        <label className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
          <Globe size={16} className="text-leaf-600" />
          {t('choose_language')}
        </label>
      )}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-leaf-600">
          <Globe size={18} />
        </div>
        <select
          value={activeLang}
          disabled={isSavingLanguage}
          onChange={(e) => handleChange(e.target.value as Language)}
          className="w-full pl-10 pr-10 py-3 rounded-2xl border border-leaf-200 bg-white text-base font-semibold text-gray-800 shadow-sm focus:border-leaf-500 focus:ring-2 focus:ring-leaf-200 outline-none appearance-none cursor-pointer"
          aria-label={t('choose_language')}
        >
          {availableLanguages.map((lang) => (
            <option key={lang.code} value={lang.code} className="py-2 text-base">
              {lang.nativeLabel} ({lang.label})
            </option>
          ))}
        </select>
        <div className="absolute inset-y-0 right-0 flex items-center pr-3.5 pointer-events-none text-gray-400">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      {saveError ? <p role="alert" className="text-xs text-red-700">{t(saveError)}</p> : null}
    </div>
  );
}
