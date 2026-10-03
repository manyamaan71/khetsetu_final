import { Language } from '../types';

const cropNames: Record<string, Partial<Record<Language, string>>> = {
  tomato: { hi: 'टमाटर', kn: 'ಟೊಮೆಟೊ', ta: 'தக்காளி', te: 'టమాటా', mr: 'टोमॅटो', bn: 'টমেটো' },
  potato: { hi: 'आलू', kn: 'ಆಲೂಗಡ್ಡೆ', ta: 'உருளைக்கிழங்கு', te: 'బంగాళాదుంప', mr: 'बटाटा', bn: 'আলু' },
  maize: { hi: 'मक्का', kn: 'ಮೆಕ್ಕೆಜೋಳ', ta: 'மக்காச்சோளம்', te: 'మొక్కజొన్న', mr: 'मका', bn: 'ভুট্টা' },
  corn: { hi: 'मक्का', kn: 'ಮೆಕ್ಕೆಜೋಳ', ta: 'மக்காச்சோளம்', te: 'మొక్కజొన్న', mr: 'मका', bn: 'ভুট্টা' },
};

const diseaseNames: Record<string, Partial<Record<Language, string>>> = {
  'common rust': { hi: 'सामान्य रस्ट', kn: 'ಸಾಮಾನ್ಯ ತುಕ್ಕು ರೋಗ', ta: 'பொதுத் துரு நோய்', te: 'సాధారణ తుప్పు తెగులు', mr: 'सामान्य तांबेरा', bn: 'সাধারণ মরিচা রোগ' },
  'early blight': { hi: 'अगेती झुलसा', kn: 'ಆರಂಭಿಕ ಅಂಗಮಾರಿ', ta: 'ஆரம்பகால கருகல் நோய்', te: 'ఎర్లీ బ్లైట్ తెగులు', mr: 'अर्ली ब्लाइट', bn: 'আর্লি ব্লাইট' },
  'late blight': { hi: 'पछेती झुलसा', kn: 'ತಡ ಅಂಗಮಾರಿ', ta: 'தாமதக் கருகல் நோய்', te: 'లేట్ బ్లైట్ తెగులు', mr: 'लेट ब्लाइट', bn: 'লেট ব্লাইট' },
  healthy: { hi: 'स्वस्थ', kn: 'ಆರೋಗ್ಯಕರ', ta: 'ஆரோக்கியமான', te: 'ఆరోగ్యకరమైన', mr: 'निरोगी', bn: 'স্বাস্থ্যকর' },
};

export function localizedCropName(name: string, language: Language): string {
  return language === 'en' ? name : cropNames[name.toLowerCase()]?.[language] ?? name;
}

export function localizedDiseaseName(name: string, language: Language): string {
  return language === 'en' ? name : diseaseNames[name.toLowerCase()]?.[language] ?? name;
}