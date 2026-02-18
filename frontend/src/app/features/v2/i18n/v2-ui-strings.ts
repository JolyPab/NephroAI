export type V2UiLang = 'es' | 'en';

export interface V2UiStrings {
  uploadLongRunningStatus: string;
  uploadAccuracyHint: string;
}

const V2_UI_STRINGS: Record<V2UiLang, V2UiStrings> = {
  es: {
    uploadLongRunningStatus: 'Subiendo... Extrayendo... Esto puede tardar unos minutos.',
    uploadAccuracyHint:
      'Nota: a veces el modelo puede equivocarse con algunos analitos. Si ves un error, elimina ese PDF en Perfil y vuelve a subirlo.',
  },
  en: {
    uploadLongRunningStatus: 'Uploading... Extracting... This can take a few minutes.',
    uploadAccuracyHint:
      'Note: the model may occasionally misread some analytes. If you see an error, delete that PDF in Profile and upload it again.',
  },
};

export function getV2LangFromStorage(): V2UiLang {
  const stored = localStorage.getItem('v2_lang');
  return stored === 'en' || stored === 'es' ? stored : 'es';
}

export function getV2UiStrings(): V2UiStrings {
  return V2_UI_STRINGS[getV2LangFromStorage()];
}
