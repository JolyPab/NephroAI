import { Component, OnInit, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

import { V2AnalyteItemResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../../v2/i18n/analyte-display';

type StatusKind = 'normal' | 'low' | 'high' | 'critical' | 'unknown' | 'categorical';
type StageTone = 'stable' | 'watch' | 'warning' | 'critical' | 'unknown';

interface KeyMetricCard {
  analyteKey: string;
  displayName: string;
  valueLabel: string;
  dateLabel: string;
  statusLabel: string;
  statusKind: StatusKind;
  refLabel: string | null;
  timestamp: number;
  priority: number;
  reason: string;
}

interface KidneyStageStatus {
  stage: string;
  label: string;
  valueLabel: string;
  dateLabel: string;
  tone: StageTone;
  todo: string;
  analyteKey: string | null;
}

interface PatientTodo {
  title: string;
  text: string;
  route: string;
  queryParams?: Record<string, string>;
}

interface DashboardSnapshot {
  latestDate: string;
  tracked: number;
  attention: number;
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
  language: V2DashboardLang = 'es';
  snapshot: DashboardSnapshot = {
    latestDate: '-',
    tracked: 0,
    attention: 0,
  };
  kidneyStage: KidneyStageStatus = this.getUnknownKidneyStage();
  criticalItems: KeyMetricCard[] = [];
  keyMetrics: KeyMetricCard[] = [];
  todos: PatientTodo[] = [];

  ngOnInit(): void {
    this.language = this.loadV2Language();
    this.v2Service.listAnalytes().subscribe({
      next: (analytes) => {
        this.analytes = [...(analytes ?? [])].sort((a, b) => this.getDateTimestamp(b) - this.getDateTimestamp(a));
        const cards = this.buildCards(this.analytes);

        this.kidneyStage = this.deriveKidneyStage(this.analytes);
        this.criticalItems = cards
          .filter((card) => this.isPatientCritical(card))
          .sort((a, b) => b.priority - a.priority || b.timestamp - a.timestamp)
          .slice(0, 5);
        this.keyMetrics = this.selectKeyMetrics(cards);
        this.snapshot = this.buildSnapshot(cards);
        this.todos = this.buildTodos();
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.DASHBOARD_LOAD_FAILED');
        this.loading = false;
      },
    });
  }

  getStatusClass(card: KeyMetricCard): string {
    return `status-pill status-pill--${card.statusKind}`;
  }

  getStageClass(): string {
    return `stage-card glass glass-strong stage-card--${this.kidneyStage.tone}`;
  }

  private buildSnapshot(cards: KeyMetricCard[]): DashboardSnapshot {
    const latestTs = Math.max(...cards.map((card) => card.timestamp), 0);
    return {
      latestDate: latestTs > 0 ? this.formatDateFromTimestamp(latestTs) : '-',
      tracked: cards.length,
      attention: cards.filter((card) => this.isPatientCritical(card)).length,
    };
  }

  private buildCards(items: V2AnalyteItemResponse[]): KeyMetricCard[] {
    return items.map((item) => {
      const reference = this.getReference(item);
      const status = this.computeStatus(item, reference);
      return {
        analyteKey: item.analyte_key,
        displayName: this.getDisplayName(item),
        valueLabel: this.getLastValueLabel(item),
        dateLabel: this.formatLastDate(item),
        statusLabel: status.label,
        statusKind: status.kind,
        refLabel: this.formatReference(reference),
        timestamp: this.getDateTimestamp(item),
        priority: status.priority,
        reason: status.reason,
      };
    });
  }

  private selectKeyMetrics(cards: KeyMetricCard[]): KeyMetricCard[] {
    const preferred = ['EGFR', 'CREATININE', 'CREATININA', 'UREA', 'BUN', 'POTASSIUM', 'POTASIO', 'SODIUM', 'SODIO', 'GLUCOSE', 'GLUCOSA'];
    const scored = cards
      .map((card) => ({
        card,
        score:
          card.priority * 10 +
          (preferred.some((key) => this.normalize(card.analyteKey).includes(key) || this.normalize(card.displayName).includes(key)) ? 5 : 0),
      }))
      .sort((a, b) => b.score - a.score || b.card.timestamp - a.card.timestamp)
      .map((item) => item.card);

    return this.uniqueCards(scored).slice(0, 6);
  }

  private buildTodos(): PatientTodo[] {
    if (!this.analytes.length) {
      return [
        {
          title: 'Subir el primer analisis',
          text: 'Carga un PDF de laboratorio para calcular el estado actual.',
          route: '/patient/upload',
        },
      ];
    }

    const todos: PatientTodo[] = [];
    if (this.kidneyStage.tone !== 'unknown' && this.kidneyStage.tone !== 'stable') {
      todos.push({
        title: `Revisar estadio ${this.kidneyStage.stage}`,
        text: this.kidneyStage.todo,
        route: '/patient/charts',
        queryParams: this.kidneyStage.analyteKey ? { analyte_key: this.kidneyStage.analyteKey } : undefined,
      });
    }

    for (const item of this.criticalItems.slice(0, 2)) {
      todos.push({
        title: `Controlar ${item.displayName}`,
        text: item.reason || 'Revisa este resultado con tu medico.',
        route: '/patient/charts',
        queryParams: { analyte_key: item.analyteKey },
      });
    }

    todos.push({
      title: 'Actualizar resultados',
      text: 'Sube el siguiente reporte para comparar la tendencia.',
      route: '/patient/upload',
    });

    return todos.slice(0, 4);
  }

  private deriveKidneyStage(items: V2AnalyteItemResponse[]): KidneyStageStatus {
    const egfr = items
      .filter((item) => this.isEgfrItem(item))
      .filter((item) => item.last_value_numeric !== null && item.last_value_numeric !== undefined)
      .sort((a, b) => this.getDateTimestamp(b) - this.getDateTimestamp(a))[0];

    if (!egfr || egfr.last_value_numeric === null || egfr.last_value_numeric === undefined) {
      return this.getUnknownKidneyStage();
    }

    const value = egfr.last_value_numeric;
    const valueLabel = this.getLastValueLabel(egfr);
    const dateLabel = this.formatLastDate(egfr);
    const analyteKey = egfr.analyte_key;

    if (value < 15) {
      return {
        stage: 'G5',
        label: 'Fallo renal por TFG',
        valueLabel,
        dateLabel,
        tone: 'critical',
        todo: 'Contacta a tu medico cuanto antes para revisar este resultado y el plan de manejo.',
        analyteKey,
      };
    }
    if (value < 30) {
      return {
        stage: 'G4',
        label: 'TFG severamente disminuida',
        valueLabel,
        dateLabel,
        tone: 'critical',
        todo: 'Agenda revision medica prioritaria y confirma creatinina, potasio y orina.',
        analyteKey,
      };
    }
    if (value < 45) {
      return {
        stage: 'G3b',
        label: 'TFG moderada a severamente disminuida',
        valueLabel,
        dateLabel,
        tone: 'warning',
        todo: 'Revisa la tendencia con tu medico y verifica albumina/proteina en orina.',
        analyteKey,
      };
    }
    if (value < 60) {
      return {
        stage: 'G3a',
        label: 'TFG moderadamente disminuida',
        valueLabel,
        dateLabel,
        tone: 'watch',
        todo: 'Da seguimiento a la TFG y confirma si el cambio persiste en controles.',
        analyteKey,
      };
    }
    return {
      stage: value < 90 ? 'G2' : 'G1',
      label: value < 90 ? 'TFG levemente disminuida' : 'TFG normal',
      valueLabel,
      dateLabel,
      tone: 'stable',
      todo: 'Mantener seguimiento regular de la tendencia.',
      analyteKey,
    };
  }

  private computeStatus(
    item: V2AnalyteItemResponse,
    reference: Record<string, unknown> | null,
  ): { kind: StatusKind; label: string; priority: number; reason: string } {
    const value = item.last_value_numeric;
    const clinical = this.computeClinicalStatus(item);
    if (clinical) {
      return clinical;
    }

    if (value === null || value === undefined || !Number.isFinite(value)) {
      return { kind: 'unknown', label: 'Sin referencia', priority: 0, reason: '' };
    }
    if (!reference) {
      return { kind: 'unknown', label: 'Sin referencia', priority: 0, reason: '' };
    }

    const type = typeof reference['type'] === 'string' ? String(reference['type']).toLowerCase() : '';
    if ((type === 'categorical' || type === 'staged') && Array.isArray(reference['categories'] ?? reference['stages'])) {
      const matched = this.matchCategoryLabel(value, (reference['categories'] ?? reference['stages']) as unknown[]);
      return { kind: 'categorical', label: matched ?? 'Sin referencia', priority: 0, reason: matched ?? '' };
    }

    const bounds = this.extractBounds(reference);
    if (bounds.min !== null && value < bounds.min) {
      return { kind: 'low', label: 'Bajo', priority: 2, reason: 'Esta por debajo del rango de referencia.' };
    }
    if (bounds.max !== null && value > bounds.max) {
      return { kind: 'high', label: 'Alto', priority: 2, reason: 'Esta por encima del rango de referencia.' };
    }
    if (bounds.min !== null || bounds.max !== null) {
      return { kind: 'normal', label: 'En rango', priority: 0, reason: '' };
    }

    return { kind: 'unknown', label: 'Sin referencia', priority: 0, reason: '' };
  }

  private computeClinicalStatus(
    item: V2AnalyteItemResponse,
  ): { kind: StatusKind; label: string; priority: number; reason: string } | null {
    const value = item.last_value_numeric;
    if (value === null || value === undefined || !Number.isFinite(value)) {
      return null;
    }
    const key = this.normalize(`${item.analyte_key} ${item.raw_name ?? ''}`);

    if (this.isEgfrItem(item)) {
      if (value < 30) return { kind: 'critical', label: 'Critico', priority: 5, reason: 'TFG menor de 30: requiere revision medica prioritaria.' };
      if (value < 45) return { kind: 'high', label: 'Atencion', priority: 4, reason: 'TFG compatible con estadio G3b.' };
      if (value < 60) return { kind: 'high', label: 'Atencion', priority: 3, reason: 'TFG compatible con estadio G3a.' };
      return { kind: 'normal', label: 'Seguimiento', priority: 1, reason: '' };
    }

    if (key.includes('POTASSIUM') || key.includes('POTASIO')) {
      if (value >= 6 || value < 3) return { kind: 'critical', label: 'Critico', priority: 5, reason: 'Potasio fuera de zona segura; consulta pronto.' };
      if (value > 5 || value < 3.5) return { kind: value > 5 ? 'high' : 'low', label: value > 5 ? 'Alto' : 'Bajo', priority: 4, reason: 'El potasio puede afectar ritmo cardiaco y debe revisarse.' };
      return { kind: 'normal', label: 'En rango', priority: 0, reason: '' };
    }

    if (key.includes('CREATININE') || key.includes('CREATININA')) {
      if (value > 2) return { kind: 'critical', label: 'Alto', priority: 4, reason: 'Creatinina elevada; correlacionar con TFG y tendencia.' };
      if (value > 1.3) return { kind: 'high', label: 'Alto', priority: 3, reason: 'Creatinina por encima de un umbral general.' };
      return { kind: 'normal', label: 'En rango', priority: 0, reason: '' };
    }

    if (key.includes('UREA') || key.includes('BUN')) {
      const isBun = key.includes('BUN');
      const high = isBun ? value > 20 : value > 50;
      if (high) return { kind: 'high', label: 'Alto', priority: 2, reason: 'Marcador renal/metabolico elevado; revisar junto con creatinina y TFG.' };
      return { kind: 'normal', label: 'En rango', priority: 0, reason: '' };
    }

    if (key.includes('SODIUM') || key.includes('SODIO')) {
      if (value < 130 || value > 150) return { kind: 'critical', label: 'Critico', priority: 5, reason: 'Sodio muy fuera de rango; requiere revision pronta.' };
      if (value < 135 || value > 145) return { kind: value > 145 ? 'high' : 'low', label: value > 145 ? 'Alto' : 'Bajo', priority: 3, reason: 'Sodio fuera del rango esperado.' };
      return { kind: 'normal', label: 'En rango', priority: 0, reason: '' };
    }

    if (key.includes('GLUCOSE') || key.includes('GLUCOSA')) {
      if (value < 70) return { kind: 'low', label: 'Bajo', priority: 4, reason: 'Glucosa baja; revisar sintomas y contexto.' };
      if (value >= 126) return { kind: 'high', label: 'Alto', priority: 3, reason: 'Glucosa elevada; confirmar si fue en ayunas.' };
      return { kind: 'normal', label: 'En rango', priority: 0, reason: '' };
    }

    if (key.includes('HEMOGLOBIN') || key.includes('HEMOGLOBINA')) {
      if (value < 10) return { kind: 'critical', label: 'Bajo', priority: 4, reason: 'Hemoglobina baja; revisar anemia y sintomas.' };
      if (value < 12) return { kind: 'low', label: 'Bajo', priority: 2, reason: 'Hemoglobina bajo umbral general.' };
      return { kind: 'normal', label: 'En rango', priority: 0, reason: '' };
    }

    if (key.includes('ALBUMIN') || key.includes('ALBUMINA') || key.includes('PROTEIN') || key.includes('PROTEINA')) {
      if (value > 0) return { kind: 'high', label: 'Detectado', priority: 3, reason: 'Proteina/albumina en orina puede ser relevante para rinon.' };
    }

    return null;
  }

  private isPatientCritical(card: KeyMetricCard): boolean {
    return card.priority >= 2 || card.statusKind === 'critical';
  }

  private uniqueCards(cards: KeyMetricCard[]): KeyMetricCard[] {
    const seen = new Set<string>();
    return cards.filter((card) => {
      const key = this.normalize(card.analyteKey);
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  private isEgfrItem(item: V2AnalyteItemResponse): boolean {
    const key = this.normalize(`${item.analyte_key} ${item.raw_name ?? ''}`);
    const unit = this.normalize(item.unit ?? '');
    return key.includes('EGFR') || key.includes('TFG') || key.includes('GFR') || key.includes('FILTRACION') || unit.includes('ML/MIN/1.73');
  }

  private getUnknownKidneyStage(): KidneyStageStatus {
    return {
      stage: '-',
      label: 'Sin TFG reciente',
      valueLabel: '-',
      dateLabel: '-',
      tone: 'unknown',
      todo: 'Sube un reporte que incluya TFG/eGFR para estimar estadio.',
      analyteKey: null,
    };
  }

  private getDisplayName(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
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
    return Number.isFinite(ts) ? this.formatDateFromTimestamp(ts) : raw;
  }

  private formatDateFromTimestamp(ts: number): string {
    return new Date(ts).toLocaleDateString('es-ES');
  }

  private loadV2Language(): V2DashboardLang {
    const stored = localStorage.getItem('v2_lang');
    return stored === 'en' || stored === 'es' ? stored : 'es';
  }

  private getDateValue(item: V2AnalyteItemResponse): string | null {
    return (item.last_date ?? (item as { created_at?: string | null }).created_at ?? null) as string | null;
  }

  private getDateTimestamp(item: V2AnalyteItemResponse): number {
    const raw = this.getDateValue(item);
    if (!raw) {
      return 0;
    }
    const ts = Date.parse(raw);
    return Number.isFinite(ts) ? ts : 0;
  }

  private getReference(item: V2AnalyteItemResponse): Record<string, unknown> | null {
    const withExtra = item as V2AnalyteItemResponse & {
      reference?: Record<string, unknown> | null;
      reference_json?: Record<string, unknown> | null;
    };
    return withExtra.reference ?? withExtra.reference_json ?? null;
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

    if ((type === 'categorical' || type === 'staged') && Array.isArray(reference['categories'] ?? reference['stages'])) {
      const lines = ((reference['categories'] ?? reference['stages']) as unknown[])
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

  private normalize(value: string): string {
    return value
      .toUpperCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }
}
