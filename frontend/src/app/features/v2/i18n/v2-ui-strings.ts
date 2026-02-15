export type V2UiLang = 'es' | 'en';

export interface V2UiStrings {
  uploadLongRunningStatus: string;
}

const V2_UI_STRINGS: Record<V2UiLang, V2UiStrings> = {
  es: {
    uploadLongRunningStatus: 'Subiendo... Extrayendo... Esto puede tardar unos minutos.',
  },
  en: {
    uploadLongRunningStatus: 'Uploading... Extracting... This can take a few minutes.',
  },
};

export function getV2LangFromStorage(): V2UiLang {
  const stored = localStorage.getItem('v2_lang');
  return stored === 'en' || stored === 'es' ? stored : 'es';
}

export function getV2UiStrings(): V2UiStrings {
  return V2_UI_STRINGS[getV2LangFromStorage()];
}
