export type V2DashboardLang = 'en' | 'es';

type LocalizedAnalyteName = Record<V2DashboardLang, string>;

const ANALYTE_DISPLAY_MAP: Record<string, LocalizedAnalyteName> = {
  GLUCOSE_FASTING_SERUM: { en: 'Fasting Glucose', es: 'Glucosa en ayunas' },
  GLUCOSE_POSTPRANDIAL_SERUM: { en: 'Postprandial Glucose', es: 'Glucosa postprandial' },
  GLUCOSE_SERUM: { en: 'Serum Glucose', es: 'Glucosa en suero' },
  GLUCOSE_URINE: { en: 'Urine Glucose', es: 'Glucosa en orina' },
  CREATININE_SERUM: { en: 'Serum Creatinine', es: 'Creatinina en suero' },
  UREA_SERUM: { en: 'Serum Urea', es: 'Urea en suero' },
  BUN_SERUM: { en: 'Blood Urea Nitrogen (BUN)', es: 'Nitrogeno ureico (BUN)' },
  EGFR: { en: 'Estimated GFR', es: 'TFG estimada' },
  SODIUM_SERUM: { en: 'Sodium', es: 'Sodio' },
  POTASSIUM_SERUM: { en: 'Potassium', es: 'Potasio' },
  CHLORIDE_SERUM: { en: 'Chloride', es: 'Cloruro' },
  AST_SERUM: { en: 'AST (TGO)', es: 'AST (TGO)' },
  ALT_SERUM: { en: 'ALT (TGP)', es: 'ALT (TGP)' },
  GGT_SERUM: { en: 'GGT', es: 'GGT' },
  ALP_SERUM: { en: 'Alkaline Phosphatase', es: 'Fosfatasa alcalina' },
  HEMOGLOBIN_BLOOD: { en: 'Hemoglobin', es: 'Hemoglobina' },
  HEMATOCRIT_BLOOD: { en: 'Hematocrit', es: 'Hematocrito' },
  RBC_BLOOD: { en: 'Red Blood Cells', es: 'Globulos rojos' },
  WBC_BLOOD: { en: 'White Blood Cells', es: 'Globulos blancos' },
  PLATELETS_BLOOD: { en: 'Platelets', es: 'Plaquetas' },
  ALBUMIN_URINE: { en: 'Urine Albumin', es: 'Albumina en orina' },
  PROTEIN_URINE: { en: 'Urine Protein', es: 'Proteina en orina' },
  KETONES_URINE: { en: 'Urine Ketones', es: 'Cetonas en orina' },
  TSH_SERUM: { en: 'TSH', es: 'TSH' },
  PSA_SERUM: { en: 'PSA', es: 'PSA' },
  VITAMIN_D_SERUM: { en: 'Vitamin D', es: 'Vitamina D' },
};

const ES_SUFFIX_OVERRIDES: Record<string, string> = {
  URINE: 'en orina',
  SERUM: 'en suero',
  BLOOD: 'en sangre',
};

export function getAnalyteDisplayName(analyteKey: string, lang: V2DashboardLang, rawName?: string | null): string {
  const normalized = (analyteKey ?? '').trim().toUpperCase();
  const mapped = ANALYTE_DISPLAY_MAP[normalized]?.[lang];
  if (mapped) {
    return mapped;
  }

  const raw = rawName?.trim();
  if (raw) {
    return raw;
  }

  return humanizeAnalyteKey(normalized || analyteKey, lang);
}

function humanizeAnalyteKey(analyteKey: string, lang: V2DashboardLang): string {
  const cleaned = analyteKey
    .trim()
    .replace(/^OTHER_/, '')
    .replace(/^OTHER$/, '')
    .replace(/_+/g, ' ')
    .trim();

  if (!cleaned) {
    return analyteKey;
  }

  const words = cleaned.split(' ').map((word) => word.toUpperCase());
  if (lang === 'es' && words.length) {
    const tail = words[words.length - 1];
    const replacement = ES_SUFFIX_OVERRIDES[tail];
    if (replacement) {
      words.pop();
      const prefix = words.map(toTitleCase).join(' ').trim();
      return `${prefix}${prefix ? ' ' : ''}${replacement}`;
    }
  }

  return words.map(toTitleCase).join(' ');
}

function toTitleCase(word: string): string {
  const lower = word.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}
