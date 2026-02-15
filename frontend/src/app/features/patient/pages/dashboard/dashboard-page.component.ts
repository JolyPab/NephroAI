import { Component, OnInit, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

import { V2AnalyteItemResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../../v2/i18n/analyte-display';

type StatusKind = 'normal' | 'low' | 'high' | 'unknown' | 'categorical';

interface KeyMetricCard {
  analyteKey: string;
  displayName: string;
  valueLabel: string;
  dateLabel: string;
  statusLabel: string;
  statusKind: StatusKind;
  refLabel: string | null;
  timestamp: number;
}

interface DashboardSnapshot {
  headline: string;
  narrative: string;
  highlights: { label: string; value: string }[];
  chips: string[];
  howComputed: string[];
  stats: {
    total: number;
    abnormal: number;
  };
}

interface HomeSummaryTexts {
  headlineWarning: (count: number) => string;
  headlineOk: string;
  narrativeWarning: (metrics: string) => string;
  narrativeOk: string;
  highlightLatest: string;
  highlightTracked: string;
  highlightNoRef: string;
  cta: string;
  howComputedLink: string;
  howComputedTitle: string;
  statusNormal: string;
  statusLow: string;
  statusHigh: string;
  statusNoRef: string;
  howComputedLines: string[];
}

@Component({
  selector: 'app-patient-dashboard-page',
  standalone: false,
  templateUrl: './dashboard-page.component.html',
  styleUrls: ['./dashboard-page.component.scss'],
})
export class PatientDashboardPageComponent implements OnInit {
  private readonly v2Service = inject(V2Service);
  private readonly translate = inject(TranslateService);

  loading = true;
  analytes: V2AnalyteItemResponse[] = [];
  errorMessage = '';
  language: V2DashboardLang = 'en';
  showHowComputed = false;
  snapshot: DashboardSnapshot = {
    headline: '',
    narrative: '',
    highlights: [],
    chips: [],
    howComputed: [],
    stats: { total: 0, abnormal: 0 },
  };
  keyMetrics: KeyMetricCard[] = [];
  attentionItems: KeyMetricCard[] = [];
  summaryTexts: HomeSummaryTexts = this.getHomeSummaryTexts('en');

  ngOnInit(): void {
    this.language = this.loadV2Language();
    this.summaryTexts = this.getHomeSummaryTexts(this.language);
    this.v2Service.listAnalytes().subscribe({
      next: (analytes) => {
        this.analytes = [...(analytes ?? [])].sort((a, b) => this.getDateTimestamp(b) - this.getDateTimestamp(a)).slice(0, 12);
        const cards = this.buildCards(this.analytes);
        const abnormal = cards.filter((card) => this.isAbnormalCard(card));
        const normal = cards.filter((card) => !this.isAbnormalCard(card));

        this.keyMetrics = [...abnormal, ...normal].slice(0, 4);
        this.attentionItems = abnormal.slice(0, 3);
        this.snapshot = this.buildSnapshot(cards, abnormal);
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.DASHBOARD_LOAD_FAILED');
        this.loading = false;
      },
    });
  }

  trackByAnalyte(_: number, item: V2AnalyteItemResponse): string {
    return item.analyte_key;
  }

  getDisplayName(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
  }

  getStatusClass(card: KeyMetricCard): string {
    return `status-pill status-pill--${card.statusKind}`;
  }

  toggleHowComputed(): void {
    this.showHowComputed = !this.showHowComputed;
  }

  private getLastValueLabel(item: V2AnalyteItemResponse): string {
    if (item.last_value_numeric !== null && item.last_value_numeric !== undefined) {
      const formatted = Number.isInteger(item.last_value_numeric)
        ? String(item.last_value_numeric)
        : item.last_value_numeric.toFixed(2).replace(/\.?0+$/, '');
      return `${formatted}${item.unit ? ` ${item.unit}` : ''}`;
    }
    if (item.last_value_text && item.last_value_text.trim()) {
      return item.last_value_text.trim();
    }
    return '-';
  }

  private formatLastDate(item: V2AnalyteItemResponse): string {
    const raw = this.getDateValue(item);
    if (!raw) {
      return '-';
    }
    const ts = Date.parse(raw);
    if (!Number.isFinite(ts)) {
      return raw;
    }
    return new Date(ts).toLocaleDateString(this.language === 'es' ? 'es-ES' : 'en-US');
  }

  private loadV2Language(): V2DashboardLang {
    const stored = localStorage.getItem('v2_lang');
    return stored === 'es' || stored === 'en' ? stored : 'en';
  }

  private getDateValue(item: V2AnalyteItemResponse): string | null {
    const candidate = (item.last_date ?? (item as { created_at?: string | null }).created_at ?? null) as string | null;
    return candidate;
  }

  private getDateTimestamp(item: V2AnalyteItemResponse): number {
    const raw = this.getDateValue(item);
    if (!raw) {
      return 0;
    }
    const ts = Date.parse(raw);
    return Number.isFinite(ts) ? ts : 0;
  }

  private buildCards(items: V2AnalyteItemResponse[]): KeyMetricCard[] {
    return items
      .map((item) => {
        const reference = this.getReference(item);
        const status = this.computeStatus(item.last_value_numeric, reference);
        return {
          analyteKey: item.analyte_key,
          displayName: this.getDisplayName(item),
          valueLabel: this.getLastValueLabel(item),
          dateLabel: this.formatLastDate(item),
          statusLabel: status.label,
          statusKind: status.kind,
          refLabel: this.formatReference(reference),
          timestamp: this.getDateTimestamp(item),
        };
      })
      .sort((a, b) => b.timestamp - a.timestamp);
  }

  private buildSnapshot(cards: KeyMetricCard[], abnormalCards: KeyMetricCard[]): DashboardSnapshot {
    const total = cards.length;
    const abnormal = abnormalCards.length;
    const noRefCount = cards.filter((card) => card.statusKind === 'unknown').length;
    const normalCards = cards.filter((card) => card.statusKind === 'normal');
    const topAttention = abnormalCards.slice(0, 2);
    const topStable = normalCards.slice(0, 1);
    const latestTs = Math.max(...cards.map((card) => card.timestamp), 0);
    const latestDate = latestTs > 0 ? new Date(latestTs).toLocaleDateString(this.language === 'es' ? 'es-ES' : 'en-US') : '-';

    const texts = this.summaryTexts;
    const attentionNames = topAttention.map((item) => item.displayName).join(', ');
    const stableName = topStable[0]?.displayName ?? '';

    const headline = abnormal > 0 ? texts.headlineWarning(abnormal) : texts.headlineOk;
    const narrative =
      abnormal > 0
        ? texts.narrativeWarning(attentionNames || '-')
        : `${texts.narrativeOk}${stableName ? ` ${stableName}.` : ''}`;

    const highlights: { label: string; value: string }[] = [
      { label: texts.highlightLatest, value: latestDate },
      { label: texts.highlightTracked, value: String(total) },
    ];
    if (noRefCount > 0) {
      highlights.push({ label: texts.highlightNoRef, value: String(noRefCount) });
    }

    const chips = topAttention.map((item) => `${item.displayName}: ${item.statusLabel}`).slice(0, 2);

    return {
      headline,
      narrative,
      highlights: highlights.slice(0, 3),
      chips,
      howComputed: texts.howComputedLines,
      stats: { total, abnormal },
    };
  }

  private computeStatus(
    valueNumeric: number | null,
    reference: Record<string, unknown> | null,
  ): { kind: StatusKind; label: string } {
    if (valueNumeric === null || valueNumeric === undefined || !Number.isFinite(valueNumeric)) {
      return { kind: 'unknown', label: this.summaryTexts.statusNoRef };
    }
    if (!reference) {
      return { kind: 'unknown', label: this.summaryTexts.statusNoRef };
    }

    const type = typeof reference['type'] === 'string' ? String(reference['type']).toLowerCase() : '';
    if (type === 'categorical' && Array.isArray(reference['categories'])) {
      const matched = this.matchCategoryLabel(valueNumeric, reference['categories']);
      return { kind: 'categorical', label: matched ?? this.summaryTexts.statusNoRef };
    }

    const bounds = this.extractBounds(reference);
    if (bounds.min !== null && valueNumeric < bounds.min) {
      return { kind: 'low', label: this.summaryTexts.statusLow };
    }
    if (bounds.max !== null && valueNumeric > bounds.max) {
      return { kind: 'high', label: this.summaryTexts.statusHigh };
    }
    if (bounds.min !== null || bounds.max !== null) {
      return { kind: 'normal', label: this.summaryTexts.statusNormal };
    }

    return { kind: 'unknown', label: this.summaryTexts.statusNoRef };
  }

  private extractBounds(reference: Record<string, unknown>): { min: number | null; max: number | null } {
    let min = this.readNumber(reference, ['min', 'lower', 'minimum']);
    let max = this.readNumber(reference, ['max', 'upper', 'maximum']);
    const threshold = this.toNumber(reference['threshold']);
    const type = typeof reference['type'] === 'string' ? String(reference['type']).toLowerCase() : '';
    if (threshold !== null) {
      if (type === 'max' && max === null) {
        max = threshold;
      }
      if (type === 'min' && min === null) {
        min = threshold;
      }
    }
    return { min, max };
  }

  private formatReference(reference: Record<string, unknown> | null): string | null {
    if (!reference) {
      return null;
    }
    const type = typeof reference['type'] === 'string' ? String(reference['type']).toLowerCase() : '';

    if (type === 'categorical' && Array.isArray(reference['categories'])) {
      const lines = (reference['categories'] as unknown[])
        .map((category) => this.formatCategorySummary(category))
        .filter((line): line is string => !!line)
        .slice(0, 4);
      return lines.length ? lines.join('; ') : null;
    }

    const bounds = this.extractBounds(reference);
    if (bounds.min !== null && bounds.max !== null) {
      return `${this.formatNumber(bounds.min)}-${this.formatNumber(bounds.max)}`;
    }
    if (bounds.max !== null) {
      return `< ${this.formatNumber(bounds.max)}`;
    }
    if (bounds.min !== null) {
      return `> ${this.formatNumber(bounds.min)}`;
    }
    return null;
  }

  private formatCategorySummary(category: unknown): string | null {
    if (!category || typeof category !== 'object' || Array.isArray(category)) {
      return null;
    }
    const item = category as Record<string, unknown>;
    const label = typeof item['label'] === 'string' ? item['label'].trim() : '';
    if (!label) {
      return null;
    }
    const min = this.toNumber(item['min']);
    const max = this.toNumber(item['max']);
    if (min !== null && max !== null) {
      return `${label} ${this.formatNumber(min)}-${this.formatNumber(max)}`;
    }
    if (max !== null) {
      return `${label} <${this.formatNumber(max)}`;
    }
    if (min !== null) {
      return `${label} >${this.formatNumber(min)}`;
    }
    return label;
  }

  private matchCategoryLabel(value: number, categoriesRaw: unknown[]): string | null {
    for (const category of categoriesRaw) {
      if (!category || typeof category !== 'object' || Array.isArray(category)) {
        continue;
      }
      const item = category as Record<string, unknown>;
      const label = typeof item['label'] === 'string' ? item['label'].trim() : '';
      const min = this.toNumber(item['min']);
      const max = this.toNumber(item['max']);
      const minOk = min === null || value >= min;
      const maxOk = max === null || value <= max;
      if (label && minOk && maxOk) {
        return label;
      }
    }
    return null;
  }

  private isAbnormalCard(card: KeyMetricCard): boolean {
    if (card.statusKind === 'low' || card.statusKind === 'high') {
      return true;
    }
    if (card.statusKind !== 'categorical') {
      return false;
    }
    const normalized = card.statusLabel
      .toUpperCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
    return ['ALTO', 'HIGH', 'RISK', 'RIESGO'].some((keyword) => normalized.includes(keyword));
  }

  private getReference(item: V2AnalyteItemResponse): Record<string, unknown> | null {
    const withExtra = item as V2AnalyteItemResponse & {
      reference?: Record<string, unknown> | null;
      reference_json?: Record<string, unknown> | null;
    };
    return withExtra.reference ?? withExtra.reference_json ?? null;
  }

  private readNumber(source: Record<string, unknown>, keys: string[]): number | null {
    for (const key of keys) {
      const value = this.toNumber(source[key]);
      if (value !== null) {
        return value;
      }
    }
    return null;
  }

  private toNumber(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value.trim().replace(',', '.'));
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  private formatNumber(value: number): string {
    if (!Number.isFinite(value)) {
      return '-';
    }
    if (Number.isInteger(value)) {
      return String(value);
    }
    return value.toFixed(2).replace(/\.?0+$/, '');
  }

  private getHomeSummaryTexts(lang: V2DashboardLang): HomeSummaryTexts {
    if (lang === 'es') {
      return {
        headlineWarning: (count) => `⚠️ Detecte ${count} metricas que requieren atencion`,
        headlineOk: '✅ Todo en rango en tus ultimos resultados',
        narrativeWarning: (metrics) => `Lo mas relevante ahora es ${metrics}. Vale la pena revisar la tendencia y el contexto clinico con tu medico.`,
        narrativeOk: 'Tus metricas principales estan estables. Puedes revisar tendencias para ver cambios.',
        highlightLatest: 'Mas reciente',
        highlightTracked: 'Seguimiento',
        highlightNoRef: 'Sin rango de referencia',
        cta: 'Analiza mis resultados',
        howComputedLink: 'Como se calcula?',
        howComputedTitle: 'Como se calcula',
        statusNormal: 'Normal',
        statusLow: 'Bajo',
        statusHigh: 'Alto',
        statusNoRef: 'Sin referencia',
        howComputedLines: [
          'Usa tus ultimos valores extraidos y los rangos de referencia del reporte.',
          'Si una metrica no tiene rango de referencia, su estado puede verse como "Sin referencia".',
          'Este resumen es informativo y no reemplaza consejo medico.',
        ],
      };
    }

    return {
      headlineWarning: (count) => `⚠️ I detected ${count} metrics that need attention`,
      headlineOk: '✅ Everything is in range in your latest results',
      narrativeWarning: (metrics) => `What matters most now is ${metrics}. It may be worth reviewing trends and context with your doctor.`,
      narrativeOk: 'Your main metrics look stable. You can open Trends to see how values changed over time.',
      highlightLatest: 'Most recent',
      highlightTracked: 'Tracked',
      highlightNoRef: 'No reference range',
      cta: 'Analyze my results',
      howComputedLink: 'How is this computed?',
      howComputedTitle: 'How this is computed',
      statusNormal: 'Normal',
      statusLow: 'Low',
      statusHigh: 'High',
      statusNoRef: 'No reference',
      howComputedLines: [
        'It uses your latest extracted values and the reference ranges in the report.',
        'If a metric has no reference range, status may show as "No reference".',
        'This is informational and not medical advice.',
      ],
    };
  }
}
