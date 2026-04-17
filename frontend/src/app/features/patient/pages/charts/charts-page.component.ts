import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { TranslateService } from '@ngx-translate/core';
import { format } from 'date-fns';
import { es as esLocale } from 'date-fns/locale';

import { V2AnalyteItemResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../../v2/i18n/analyte-display';
import { AdviceClientService } from '../../../../core/services/advice.service';
import { SeriesReadyPayload } from '../../../v2/pages/series/v2-series-page.component';

const COLOR_NORMAL = '#34d399';
const COLOR_ABNORMAL = '#f87171';
const COLOR_UNKNOWN = 'rgba(255,255,255,0.22)';

@Component({
  selector: 'app-patient-charts-page',
  standalone: false,
  templateUrl: './charts-page.component.html',
  styleUrls: ['./charts-page.component.scss'],
})
export class PatientChartsPageComponent implements OnInit {
  private readonly v2Service = inject(V2Service);
  private readonly translate = inject(TranslateService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly adviceService = inject(AdviceClientService);

  analytes: V2AnalyteItemResponse[] = [];
  selectedMetric = '';
  isLoading = true;
  errorMessage = '';
  language: V2DashboardLang = 'es';
  sidebarSearch = '';

  // Stat card values
  statLastValue = '';
  statUnit = '';
  statAverage = '';
  statVariation = '';
  statVariationPeriod = '';
  statStatus: 'normal' | 'abnormal' | null = null;
  statLastDate = '';

  // IA Asistente
  copilotMessage = '';
  copilotLoading = false;
  copilotKey = '';

  // Status dots: populated lazily as user browses metrics
  statusMap = new Map<string, 'normal' | 'abnormal'>();

  private dataVersion = '';
  private pendingSelectedAnalyteKey: string | null = null;

  ngOnInit(): void {
    this.language = this.loadV2Language();
    this.route.queryParamMap.subscribe((params) => {
      const requested = params.get('analyte_key');
      if (!requested) return;
      if (this.analytes.some((item) => item.analyte_key === requested)) {
        this.selectedMetric = requested;
        return;
      }
      this.pendingSelectedAnalyteKey = requested;
    });
    this.loadAnalytes();
  }

  onMetricChange(metric: string): void {
    if (this.selectedMetric === metric) return;
    this.selectedMetric = metric;
    this.clearStats();
    this.syncQueryMetric(metric);
  }

  getDisplayName(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
  }

  getDisplayNameByKey(key: string): string {
    const analyte = this.analytes.find((a) => a.analyte_key === key);
    return getAnalyteDisplayName(key, this.language, analyte?.raw_name);
  }

  getMetricColor(key: string): string {
    const status = this.statusMap.get(key);
    if (status === 'normal') return COLOR_NORMAL;
    if (status === 'abnormal') return COLOR_ABNORMAL;
    return COLOR_UNKNOWN;
  }

  get filteredSidebarAnalytes(): V2AnalyteItemResponse[] {
    const term = this.sidebarSearch.trim().toLowerCase();
    const list = this.analytes.filter((a) => {
      if (!term) return true;
      const name = this.getDisplayName(a).toLowerCase();
      return name.includes(term) || a.analyte_key.toLowerCase().includes(term);
    });
    return list.sort((a, b) => this.getDisplayName(a).localeCompare(this.getDisplayName(b), this.language));
  }

  get selectedAnalyte(): V2AnalyteItemResponse | undefined {
    return this.analytes.find((a) => a.analyte_key === this.selectedMetric);
  }

  onSeriesDataReady(payload: SeriesReadyPayload): void {
    const { series, refMin, refMax } = payload;

    const numericPoints = [...series.points]
      .filter((p): p is typeof p & { y: number } => p.y !== null && p.y !== undefined)
      .sort((a, b) => this.tsOrZero(a.t) - this.tsOrZero(b.t));

    if (!numericPoints.length) {
      this.clearStats();
      return;
    }

    const lastPoint = numericPoints[numericPoints.length - 1];
    const unit = series.unit ?? '';
    this.statLastValue = this.formatNum(lastPoint.y);
    this.statUnit = unit;
    this.statLastDate = lastPoint.t ? format(new Date(Date.parse(lastPoint.t)), "d 'de' MMMM, yyyy", { locale: esLocale }) : '';

    const avg = numericPoints.reduce((s, p) => s + p.y, 0) / numericPoints.length;
    this.statAverage = this.formatNum(avg);

    // Variation: compute % change and period label
    if (numericPoints.length >= 2) {
      const firstPoint = numericPoints[0];
      const firstTs = this.tsOrZero(firstPoint.t);
      const lastTs = this.tsOrZero(lastPoint.t);
      const pct = firstPoint.y !== 0
        ? ((lastPoint.y - firstPoint.y) / Math.abs(firstPoint.y)) * 100
        : 0;
      const sign = pct > 0 ? '+' : '';
      this.statVariation = `${sign}${this.formatNum(pct)}%`;
      const monthsDiff = Math.round((lastTs - firstTs) / (30 * 24 * 3600 * 1000));
      this.statVariationPeriod = monthsDiff > 0
        ? `en ${monthsDiff} ${monthsDiff === 1 ? 'mes' : 'meses'}`
        : '';
    } else {
      this.statVariation = '-';
      this.statVariationPeriod = '';
    }

    // Status
    if (refMin !== undefined || refMax !== undefined) {
      const val = lastPoint.y;
      const isLow = refMin !== undefined && val < refMin;
      const isHigh = refMax !== undefined && val > refMax;
      this.statStatus = isLow || isHigh ? 'abnormal' : 'normal';
    } else {
      this.statStatus = null;
    }

    if (this.statStatus) {
      this.statusMap.set(this.selectedMetric, this.statStatus);
    }

    // Copilot — only reload if metric actually changed
    if (this.copilotKey !== this.selectedMetric) {
      this.copilotKey = this.selectedMetric;
      this.loadCopilot(this.selectedMetric);
    }
  }

  get variationIsPositive(): boolean {
    return this.statVariation.startsWith('+');
  }

  get variationIsNegative(): boolean {
    return this.statVariation.startsWith('-');
  }

  get statusLabel(): string {
    if (this.statStatus === 'normal') return this.language === 'es' ? 'Normal' : 'Normal';
    if (this.statStatus === 'abnormal') return this.language === 'es' ? 'Anormal' : 'Abnormal';
    return '-';
  }

  formatCopilotHtml(text: string): SafeHtml {
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    const withBold = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    return this.sanitizer.bypassSecurityTrustHtml(withBold);
  }

  trackByAnalyte(_: number, item: V2AnalyteItemResponse): string {
    return item.analyte_key;
  }

  private clearStats(): void {
    this.statLastValue = '';
    this.statUnit = '';
    this.statAverage = '';
    this.statVariation = '';
    this.statVariationPeriod = '';
    this.statStatus = null;
    this.statLastDate = '';
    this.copilotMessage = '';
    this.copilotLoading = false;
  }

  private loadCopilot(analyteKey: string): void {
    const cached = this.getCopilotCache(analyteKey);
    if (cached) {
      this.copilotMessage = cached;
      this.copilotLoading = false;
      return;
    }
    const name = this.getDisplayNameByKey(analyteKey);
    this.copilotMessage = '';
    this.copilotLoading = true;
    this.adviceService
      .ask(
        `Dame un breve análisis del estado actual de ${name} basado en mis últimos análisis. Responde en 1-2 oraciones.`,
        [name],
        180,
        'es',
      )
      .subscribe({
        next: (res) => {
          this.copilotLoading = false;
          this.copilotMessage = res.answer ?? '';
          if (this.copilotMessage) this.setCopilotCache(analyteKey, this.copilotMessage);
        },
        error: () => {
          this.copilotLoading = false;
        },
      });
  }

  private getCopilotCache(analyteKey: string): string | null {
    try {
      return localStorage.getItem(`copilot_${analyteKey}_${this.dataVersion}`);
    } catch { return null; }
  }

  private setCopilotCache(analyteKey: string, message: string): void {
    try {
      localStorage.setItem(`copilot_${analyteKey}_${this.dataVersion}`, message);
    } catch {}
  }

  private loadAnalytes(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.v2Service.listAnalytes().subscribe({
      next: (rows) => {
        this.analytes = rows ?? [];
        this.dataVersion = [...this.analytes]
          .map((a) => a.last_date ?? '')
          .filter(Boolean)
          .sort()
          .at(-1) ?? 'v0';
        const availableKeys = new Set(this.analytes.map((item) => item.analyte_key));

        if (!this.selectedMetric || !availableKeys.has(this.selectedMetric)) {
          this.selectedMetric = this.sortByDisplay(this.analytes)[0]?.analyte_key ?? '';
        }
        if (this.pendingSelectedAnalyteKey && availableKeys.has(this.pendingSelectedAnalyteKey)) {
          this.selectedMetric = this.pendingSelectedAnalyteKey;
          this.pendingSelectedAnalyteKey = null;
        }
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.METRICS_LOAD_FAILED');
        this.isLoading = false;
      },
    });
  }

  private loadV2Language(): V2DashboardLang {
    const stored = localStorage.getItem('v2_lang');
    return stored === 'es' || stored === 'en' ? stored : 'es';
  }

  private sortByDisplay(items: V2AnalyteItemResponse[]): V2AnalyteItemResponse[] {
    const copy = [...items];
    copy.sort((a, b) => this.getDisplayName(a).localeCompare(this.getDisplayName(b), this.language));
    return copy;
  }

  private syncQueryMetric(metric: string): void {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { analyte_key: metric },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  private tsOrZero(val: string | null): number {
    if (!val) return 0;
    const ts = Date.parse(val);
    return Number.isFinite(ts) ? ts : 0;
  }

  private formatNum(value: number): string {
    if (!Number.isFinite(value)) return '-';
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(1).replace(/\.?0+$/, '');
  }
}
