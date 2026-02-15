import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, ViewChild, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import Chart from 'chart.js/auto';
import { ChartConfiguration, ChartEvent, ScriptableContext, TooltipItem } from 'chart.js';
import annotationPlugin from 'chartjs-plugin-annotation';
import zoomPlugin from 'chartjs-plugin-zoom';
import { format } from 'date-fns';
import { BaseChartDirective } from 'ng2-charts';

import { V2DoctorNoteResponse, V2SeriesPointResponse, V2SeriesResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { ThemeService } from '../../../../core/services/theme.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../i18n/analyte-display';
import { SharedModule } from '../../../../shared/shared.module';
import { V2PointDetailPanelComponent } from '../../components/point-detail-panel/v2-point-detail-panel.component';

type LineChartConfig = ChartConfiguration<'line', (number | null)[], string>;
interface NumericReferenceBounds {
  refMin?: number;
  refMax?: number;
}
interface CategoricalReferenceBand {
  label: string;
  min: number | null;
  max: number | null;
  backgroundColor: string;
  borderColor: string;
}
interface ZoneLegendItem {
  label: string;
  color: string;
  borderColor: string;
}
type NumericStatus = 'normal' | 'low' | 'high' | 'unknown';
type BinaryCanonical = 'positive' | 'negative' | 'unknown';
interface ChartThemeColors {
  text: string;
  grid: string;
  tooltipBg: string;
  tooltipText: string;
  tooltipBorder: string;
}

const STATUS_LABELS: Record<V2DashboardLang, Record<NumericStatus, string>> = {
  en: { normal: 'Normal', low: 'Low', high: 'High', unknown: 'Unknown' },
  es: { normal: 'Normal', low: 'Bajo', high: 'Alto', unknown: 'Desconocido' },
};

const BINARY_LABELS: Record<V2DashboardLang, Record<BinaryCanonical, string>> = {
  en: { positive: 'Positive', negative: 'Negative', unknown: 'Unknown' },
  es: { positive: 'Positivo', negative: 'Negativo', unknown: 'Desconocido' },
};

Chart.register(zoomPlugin, annotationPlugin);

@Component({
  selector: 'app-v2-series-page',
  standalone: true,
  imports: [CommonModule, SharedModule, V2PointDetailPanelComponent],
  templateUrl: './v2-series-page.component.html',
  styleUrls: ['./v2-series-page.component.scss'],
})
export class V2SeriesPageComponent implements OnInit, OnChanges {
  private readonly route = inject(ActivatedRoute);
  private readonly v2Service = inject(V2Service);
  private readonly themeService = inject(ThemeService);
  @ViewChild(BaseChartDirective) private chartRef?: BaseChartDirective<'line'>;

  @Input() analyteKeyInput: string | null = null;
  @Input() doctorPatientId: string | number | null = null;
  @Input() embedded = false;
  @Output() pointSelected = new EventEmitter<V2SeriesPointResponse>();

  analyteKey = '';
  series: V2SeriesResponse | null = null;
  isLoading = true;
  errorMessage = '';
  headerPointCount = 0;
  headerDateRange = '-';
  headerUnit = '-';
  referenceBounds: NumericReferenceBounds = {};
  categoricalReferenceBands: CategoricalReferenceBand[] = [];
  detailPoint: V2SeriesPointResponse | null = null;
  isDetailOpen = false;
  detailDoctorNotes: V2DoctorNoteResponse[] = [];
  pointDoctorNotes = new Map<string, V2DoctorNoteResponse[]>();
  allNumericPoints: V2SeriesPointResponse[] = [];
  selectedPointIndex: number | null = null;
  selectedPointKey = '';
  language: V2DashboardLang = 'en';
  abnormalOnly = false;
  positivesOnly = false;
  headerAbnormalCount: number | null = null;
  detailValueLabel: string | null = null;
  detailStatusLabel: string | null = null;

  chartData: LineChartConfig['data'] = {
    labels: [],
    datasets: [],
  };

  chartOptions: LineChartConfig['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: 'rgba(255, 255, 255, 0.9)',
        },
      },
      tooltip: {
        filter: (ctx) => ctx.datasetIndex === 0,
        callbacks: {
          title: (items: TooltipItem<'line'>[]) => {
            if (!items.length) {
              return '';
            }
            return this.chartData.labels?.[items[0].dataIndex] ?? '';
          },
          label: (ctx: TooltipItem<'line'>) => {
            const point = this.allNumericPoints[ctx.dataIndex];
            const value = Number(ctx.parsed.y ?? point?.y);
            const unit = this.series?.unit ? ` ${this.series.unit}` : '';
            const valueLabel = `Value: ${this.formatNumber(value)}${unit}`;
            const statusLabel = this.getPointStatusLabel(point);
            const hasMin = this.referenceBounds.refMin !== undefined && this.referenceBounds.refMin !== null;
            const hasMax = this.referenceBounds.refMax !== undefined && this.referenceBounds.refMax !== null;
            if (!hasMin && !hasMax) {
              return `${valueLabel} | Status: ${statusLabel}`;
            }
            return `${valueLabel} | Status: ${statusLabel} | Ref: ${this.formatReferenceRangeLabel(this.referenceBounds)}`;
          },
        },
      },
      annotation: {
        annotations: {},
      },
      zoom: {
        pan: {
          enabled: true,
          mode: 'xy',
          threshold: 2,
        },
        zoom: {
          wheel: {
            enabled: true,
          },
          pinch: {
            enabled: true,
          },
          mode: 'xy',
        },
      },
    },
    scales: {
      x: {
        offset: true,
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
          maxRotation: 0,
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.08)',
        },
      },
      y: {
        suggestedMin: undefined,
        suggestedMax: undefined,
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.08)',
        },
      },
    },
  };

  ngOnInit(): void {
    this.language = this.loadV2Language();
    toObservable(this.themeService.theme)
      .pipe(takeUntilDestroyed())
      .subscribe(() => {
        if (this.series?.series_type === 'numeric') {
          this.buildNumericChart(this.series);
          return;
        }
        this.applyChartThemeColors();
      });
    if (this.analyteKeyInput && this.analyteKeyInput.trim() && !this.analyteKey) {
      this.analyteKey = this.analyteKeyInput;
      this.loadSeries(this.analyteKey);
      return;
    }
    this.route.paramMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const analyteKey = params.get('analyteKey');
      if (!analyteKey) {
        this.errorMessage = 'Missing analyte key.';
        this.series = null;
        this.isLoading = false;
        return;
      }
      this.analyteKey = analyteKey;
      this.loadSeries(analyteKey);
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ('analyteKeyInput' in changes) {
      const nextKey = this.analyteKeyInput?.trim() ?? '';
      if (!nextKey || nextKey === this.analyteKey) {
        return;
      }
      this.analyteKey = nextKey;
      this.loadSeries(nextKey);
      return;
    }
    if ('doctorPatientId' in changes && this.analyteKey) {
      this.loadSeries(this.analyteKey);
    }
  }

  get isNumeric(): boolean {
    return this.series?.series_type === 'numeric';
  }

  get isBinary(): boolean {
    return this.series?.series_type === 'binary';
  }

  get hasReferenceBounds(): boolean {
    return (
      (this.referenceBounds.refMin !== undefined && this.referenceBounds.refMin !== null) ||
      (this.referenceBounds.refMax !== undefined && this.referenceBounds.refMax !== null)
    );
  }

  get hasCategoricalReference(): boolean {
    return this.categoricalReferenceBands.length > 0;
  }

  get timelinePoints(): V2SeriesPointResponse[] {
    const points = this.series?.points ?? [];
    const sorted = [...points].sort((a, b) => this.timestampOrZero(b.t) - this.timestampOrZero(a.t));
    if (!this.isBinary || !this.positivesOnly) {
      return sorted;
    }
    return sorted.filter((point) => this.normalizeBinary(point.text) === 'positive');
  }

  get analyteDisplayName(): string {
    return getAnalyteDisplayName(this.analyteKey, this.language);
  }

  get zoneLegendItems(): ZoneLegendItem[] {
    if (!this.hasCategoricalReference) {
      return [];
    }
    return this.categoricalReferenceBands.map((band) => ({
      label: band.label,
      color: band.backgroundColor,
      borderColor: band.borderColor,
    }));
  }

  private loadSeries(analyteKey: string): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.closeDetail();
    this.selectedPointIndex = null;
    this.selectedPointKey = '';
    this.abnormalOnly = false;
    this.positivesOnly = false;
    const doctorScopedPatientId = this.doctorPatientId !== null ? `${this.doctorPatientId}`.trim() : '';
    const request$ = doctorScopedPatientId
      ? this.v2Service.getPatientSeries(doctorScopedPatientId, analyteKey)
      : this.v2Service.getSeries(analyteKey);

    request$.subscribe({
      next: (series) => {
        this.series = series;
        this.updateHeaderStats(series);
        this.loadDoctorNotes(series.analyte_key);
        this.isLoading = false;
        if (series.series_type === 'numeric') {
          this.buildNumericChart(series);
        } else {
          this.referenceBounds = {};
          this.categoricalReferenceBands = [];
          this.allNumericPoints = [];
          this.headerAbnormalCount = null;
          this.chartData = { labels: [], datasets: [] };
        }
      },
      error: (err) => {
        this.series = null;
        this.isLoading = false;
        this.errorMessage = err?.error?.detail ?? 'Failed to load V2 series.';
      },
    });
  }

  private buildNumericChart(series: V2SeriesResponse): void {
    const allPoints = [...series.points].sort((a, b) => this.timestampOrZero(a.t) - this.timestampOrZero(b.t));
    this.allNumericPoints = allPoints;
    this.referenceBounds = this.extractReferenceBounds(series.reference);
    this.categoricalReferenceBands = this.extractCategoricalReferenceBands(series.reference);
    const statuses = allPoints.map((point) => this.getNumericStatus(point));
    this.headerAbnormalCount = !this.hasCategoricalReference && this.hasReferenceBounds
      ? statuses.filter((status) => status === 'low' || status === 'high').length
      : null;

    const labels = allPoints.map((point) => this.formatPointDate(point.t));
    const displayPoints = allPoints.map((point) => (point.y !== null && point.y !== undefined ? point.y : null));
    const maskedData = displayPoints.map((value, index) => {
      const status = statuses[index];
      if (value === null) {
        return null;
      }
      if (this.abnormalOnly && !this.hasCategoricalReference && this.hasReferenceBounds && status !== 'low' && status !== 'high') {
        return null;
      }
      return value;
    });
    const labelSuffix = series.unit ? ` (${series.unit})` : '';
    const datasets: LineChartConfig['data']['datasets'] = [
      {
        label: `${series.analyte_key}${labelSuffix}`,
        data: maskedData,
        borderColor: 'rgba(118, 168, 255, 0.92)',
        backgroundColor: 'rgba(118, 168, 255, 0.22)',
        borderWidth: 2,
        tension: 0.3,
        pointRadius: (ctx: ScriptableContext<'line'>) => {
          const idx = ctx.dataIndex;
          const value = maskedData[idx];
          if (value === null || value === undefined) {
            return 0;
          }
          const isSelected = this.selectedPointIndex === idx;
          if (this.hasCategoricalReference) {
            return isSelected ? 7 : 4;
          }
          const status = statuses[idx];
          if (isSelected) {
            return 8;
          }
          return status === 'low' || status === 'high' ? 6 : 4;
        },
        pointHoverRadius: (ctx: ScriptableContext<'line'>) => {
          const idx = ctx.dataIndex;
          const value = maskedData[idx];
          if (value === null || value === undefined) {
            return 0;
          }
          const isSelected = this.selectedPointIndex === idx;
          if (this.hasCategoricalReference) {
            return isSelected ? 9 : 6;
          }
          const status = statuses[idx];
          if (isSelected) {
            return 10;
          }
          return status === 'low' || status === 'high' ? 8 : 6;
        },
        pointBackgroundColor: (ctx: ScriptableContext<'line'>) => {
          const isSelected = this.selectedPointIndex === ctx.dataIndex;
          if (this.hasCategoricalReference) {
            return isSelected ? 'rgba(255, 215, 0, 0.98)' : 'rgba(118, 168, 255, 0.95)';
          }
          const status = statuses[ctx.dataIndex];
          if (isSelected) {
            return 'rgba(255, 215, 0, 0.98)';
          }
          return status === 'low' || status === 'high' ? 'rgba(255, 99, 132, 0.95)' : 'rgba(118, 168, 255, 0.95)';
        },
        pointBorderColor: (ctx: ScriptableContext<'line'>) => {
          const isSelected = this.selectedPointIndex === ctx.dataIndex;
          if (this.hasCategoricalReference) {
            return isSelected ? 'rgba(255, 234, 160, 1)' : 'rgba(255, 255, 255, 0.9)';
          }
          const status = statuses[ctx.dataIndex];
          if (isSelected) {
            return 'rgba(255, 234, 160, 1)';
          }
          return status === 'low' || status === 'high' ? 'rgba(255, 220, 220, 0.95)' : 'rgba(255, 255, 255, 0.9)';
        },
        pointBorderWidth: (ctx: ScriptableContext<'line'>) => {
          const isSelected = this.selectedPointIndex === ctx.dataIndex;
          if (this.hasCategoricalReference) {
            return isSelected ? 3 : 2;
          }
          const status = statuses[ctx.dataIndex];
          if (isSelected) {
            return 3.5;
          }
          return status === 'low' || status === 'high' ? 2.5 : 2;
        },
      },
    ];

    this.chartData = {
      labels,
      datasets,
    };

    const axisBounds = this.computeAxisBounds(allPoints);
    const themeColors = this.getChartThemeColors();
    const currentOptions = (this.chartOptions ?? {}) as Record<string, unknown>;
    const currentScales = (currentOptions['scales'] ?? {}) as Record<string, unknown>;
    const currentX = (currentScales['x'] ?? {}) as Record<string, unknown>;
    const currentY = (currentScales['y'] ?? {}) as Record<string, unknown>;
    const currentPlugins = (currentOptions['plugins'] ?? {}) as Record<string, unknown>;
    const currentLegend = (currentPlugins['legend'] ?? {}) as Record<string, unknown>;
    const currentLegendLabels = (currentLegend['labels'] ?? {}) as Record<string, unknown>;
    const currentTooltip = (currentPlugins['tooltip'] ?? {}) as Record<string, unknown>;
    const currentAnnotation = (currentPlugins['annotation'] ?? {}) as Record<string, unknown>;
    const currentXTicks = (currentX['ticks'] ?? {}) as Record<string, unknown>;
    const currentYTicks = (currentY['ticks'] ?? {}) as Record<string, unknown>;
    const currentXGrid = (currentX['grid'] ?? {}) as Record<string, unknown>;
    const currentYGrid = (currentY['grid'] ?? {}) as Record<string, unknown>;
    this.chartOptions = {
      ...(this.chartOptions ?? {}),
      plugins: {
        ...currentPlugins,
        legend: {
          ...currentLegend,
          labels: {
            ...currentLegendLabels,
            color: themeColors.text,
          },
        },
        tooltip: {
          ...currentTooltip,
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipText,
          bodyColor: themeColors.tooltipText,
          borderColor: themeColors.tooltipBorder,
          borderWidth: 1,
        },
        annotation: {
          ...currentAnnotation,
          annotations: this.buildReferenceAnnotations(labels.length, axisBounds) as any,
        },
      },
      scales: {
        ...currentScales,
        ['x']: {
          ...currentX,
          offset: true,
          ticks: {
            ...currentXTicks,
            color: themeColors.text,
            maxRotation: 0,
          },
          grid: {
            ...currentXGrid,
            color: themeColors.grid,
          },
        },
        ['y']: {
          ...currentY,
          ticks: {
            ...currentYTicks,
            color: themeColors.text,
          },
          grid: {
            ...currentYGrid,
            color: themeColors.grid,
          },
          suggestedMin: axisBounds.suggestedMin,
          suggestedMax: axisBounds.suggestedMax,
        },
      },
    };
  }

  formatPointDate(value: string | null): string {
    if (!value) {
      return '-';
    }
    const ts = Date.parse(value);
    if (!Number.isFinite(ts)) {
      return value;
    }
    return format(new Date(ts), 'dd.MM.yyyy');
  }

  displayTextValue(point: V2SeriesPointResponse): string {
    if (point.text && point.text.trim()) {
      return point.text;
    }
    if (point.y !== null && point.y !== undefined) {
      return this.formatNumber(point.y);
    }
    if (this.isBinary) {
      return this.getBinaryLabel(this.normalizeBinary(point.text));
    }
    return '-';
  }

  onChartClick(evt: { event?: ChartEvent; active?: unknown[] }): void {
    const active = (evt.active ?? []).filter((item): item is { datasetIndex: number; index: number } =>
      this.isChartActiveElement(item),
    );
    if (!active.length) {
      return;
    }
    const pointHit = active.find((entry) => entry.datasetIndex === 0);
    if (!pointHit) {
      return;
    }
    const picked = this.allNumericPoints[pointHit.index];
    if (!picked) {
      return;
    }
    this.selectNumericPoint(pointHit.index);
    const native = (evt.event as { native?: Event } | undefined)?.native;
    const mouseEvent = native instanceof MouseEvent ? native : null;
    if (mouseEvent && (mouseEvent.ctrlKey || mouseEvent.metaKey)) {
      this.openDetail(picked);
    }
  }

  openDetail(point: V2SeriesPointResponse): void {
    this.detailPoint = point;
    this.detailDoctorNotes = this.pointDoctorNotes.get(this.toPointKey(point.t)) ?? [];
    this.detailValueLabel = this.getPointValueLabel(point);
    if (this.isNumeric) {
      const status = this.getPointStatusLabel(point);
      const hasRef = this.hasReferenceBounds;
      this.detailStatusLabel = hasRef ? `${status} | Ref: ${this.formatReferenceRangeLabel(this.referenceBounds)}` : status;
    } else {
      this.detailStatusLabel = null;
    }
    this.isDetailOpen = true;
  }

  openSelectedEvidence(): void {
    const point = this.getSelectedPoint();
    if (!point) {
      return;
    }
    this.openDetail(point);
  }

  onTimelineRowClick(point: V2SeriesPointResponse): void {
    this.selectedPointIndex = null;
    this.selectedPointKey = this.toPointKey(point.t);
    this.pointSelected.emit(point);
  }

  isPointSelected(point: V2SeriesPointResponse): boolean {
    return this.toPointKey(point.t) === this.selectedPointKey;
  }

  closeDetail(): void {
    this.isDetailOpen = false;
    this.detailPoint = null;
    this.detailDoctorNotes = [];
    this.detailValueLabel = null;
    this.detailStatusLabel = null;
  }

  onAbnormalOnlyChange(enabled: boolean): void {
    this.abnormalOnly = enabled;
    if (this.series?.series_type === 'numeric') {
      this.buildNumericChart(this.series);
    }
  }

  onPositivesOnlyChange(enabled: boolean): void {
    this.positivesOnly = enabled;
  }

  onResetView(): void {
    this.chartRef?.chart?.resetZoom();
    this.chartRef?.update();
  }

  private selectNumericPoint(index: number): void {
    const point = this.allNumericPoints[index];
    if (!point) {
      return;
    }
    this.selectedPointIndex = index;
    this.selectedPointKey = this.toPointKey(point.t);
    this.pointSelected.emit(point);
    if (this.series?.series_type === 'numeric') {
      this.buildNumericChart(this.series);
      this.chartRef?.update();
    }
  }

  private getSelectedPoint(): V2SeriesPointResponse | null {
    if (this.isNumeric && this.selectedPointIndex !== null) {
      return this.allNumericPoints[this.selectedPointIndex] ?? null;
    }
    if (!this.selectedPointKey) {
      return null;
    }
    const points = this.series?.points ?? [];
    return points.find((point) => this.toPointKey(point.t) === this.selectedPointKey) ?? null;
  }

  private timestampOrZero(value: string | null): number {
    if (!value) {
      return 0;
    }
    const ts = Date.parse(value);
    return Number.isFinite(ts) ? ts : 0;
  }

  private loadV2Language(): V2DashboardLang {
    const stored = localStorage.getItem('v2_lang');
    return stored === 'es' || stored === 'en' ? stored : 'en';
  }

  private loadDoctorNotes(analyteKey: string): void {
    const doctorScopedPatientId = this.doctorPatientId !== null ? `${this.doctorPatientId}`.trim() : '';
    const request$ = doctorScopedPatientId
      ? this.v2Service.listDoctorNotes(doctorScopedPatientId, analyteKey)
      : this.v2Service.listMyNotes(analyteKey);

    request$.subscribe({
      next: (notes) => {
        const grouped = new Map<string, V2DoctorNoteResponse[]>();
        (notes ?? []).forEach((note) => {
          const key = this.toPointKey(note.t);
          if (!key) {
            return;
          }
          const arr = grouped.get(key) ?? [];
          arr.push(note);
          grouped.set(key, arr);
        });
        this.pointDoctorNotes = grouped;
        if (this.detailPoint) {
          this.detailDoctorNotes = grouped.get(this.toPointKey(this.detailPoint.t)) ?? [];
        }
      },
      error: () => {
        this.pointDoctorNotes = new Map<string, V2DoctorNoteResponse[]>();
        if (this.detailPoint) {
          this.detailDoctorNotes = [];
        }
      },
    });
  }

  private toPointKey(value: string | null): string {
    if (!value) {
      return '';
    }
    const ts = Date.parse(value);
    if (!Number.isFinite(ts)) {
      return value;
    }
    return new Date(ts).toISOString();
  }

  private applyChartThemeColors(): void {
    const themeColors = this.getChartThemeColors();
    const currentOptions = (this.chartOptions ?? {}) as Record<string, unknown>;
    const currentScales = (currentOptions['scales'] ?? {}) as Record<string, unknown>;
    const currentX = (currentScales['x'] ?? {}) as Record<string, unknown>;
    const currentY = (currentScales['y'] ?? {}) as Record<string, unknown>;
    const currentPlugins = (currentOptions['plugins'] ?? {}) as Record<string, unknown>;
    const currentLegend = (currentPlugins['legend'] ?? {}) as Record<string, unknown>;
    const currentLegendLabels = (currentLegend['labels'] ?? {}) as Record<string, unknown>;
    const currentTooltip = (currentPlugins['tooltip'] ?? {}) as Record<string, unknown>;
    const currentXTicks = (currentX['ticks'] ?? {}) as Record<string, unknown>;
    const currentYTicks = (currentY['ticks'] ?? {}) as Record<string, unknown>;
    const currentXGrid = (currentX['grid'] ?? {}) as Record<string, unknown>;
    const currentYGrid = (currentY['grid'] ?? {}) as Record<string, unknown>;

    this.chartOptions = {
      ...(this.chartOptions ?? {}),
      plugins: {
        ...currentPlugins,
        legend: {
          ...currentLegend,
          labels: {
            ...currentLegendLabels,
            color: themeColors.text,
          },
        },
        tooltip: {
          ...currentTooltip,
          backgroundColor: themeColors.tooltipBg,
          titleColor: themeColors.tooltipText,
          bodyColor: themeColors.tooltipText,
          borderColor: themeColors.tooltipBorder,
          borderWidth: 1,
        },
      },
      scales: {
        ...currentScales,
        ['x']: {
          ...currentX,
          offset: true,
          ticks: {
            ...currentXTicks,
            color: themeColors.text,
          },
          grid: {
            ...currentXGrid,
            color: themeColors.grid,
          },
        },
        ['y']: {
          ...currentY,
          ticks: {
            ...currentYTicks,
            color: themeColors.text,
          },
          grid: {
            ...currentYGrid,
            color: themeColors.grid,
          },
        },
      },
    };
  }

  private getChartThemeColors(): ChartThemeColors {
    const styles = getComputedStyle(document.documentElement);
    const text = this.readCssVar(styles, '--chart-text') ?? this.readCssVar(styles, '--text') ?? '#1a1f33';
    const grid = this.readCssVar(styles, '--chart-grid') ?? 'rgba(76, 84, 112, 0.25)';
    const tooltipBg = this.readCssVar(styles, '--chart-tooltip-bg') ?? 'rgba(16, 22, 36, 0.92)';
    const tooltipText = this.readCssVar(styles, '--chart-tooltip-text') ?? text;
    const tooltipBorder = this.readCssVar(styles, '--chart-tooltip-border') ?? grid;
    return { text, grid, tooltipBg, tooltipText, tooltipBorder };
  }

  private readCssVar(styles: CSSStyleDeclaration, name: string): string | null {
    const value = styles.getPropertyValue(name).trim();
    return value || null;
  }

  private isChartActiveElement(value: unknown): value is { datasetIndex: number; index: number } {
    if (!value || typeof value !== 'object') {
      return false;
    }
    const candidate = value as { datasetIndex?: unknown; index?: unknown };
    return typeof candidate.datasetIndex === 'number' && typeof candidate.index === 'number';
  }

  private updateHeaderStats(series: V2SeriesResponse): void {
    this.headerPointCount = series.points.length;
    this.headerUnit = series.unit ?? '-';
    const timestamps = series.points
      .map((point) => this.timestampOrZero(point.t))
      .filter((ts) => ts > 0)
      .sort((a, b) => a - b);
    if (!timestamps.length) {
      this.headerDateRange = '-';
      return;
    }
    const start = format(new Date(timestamps[0]), 'dd.MM.yyyy');
    const end = format(new Date(timestamps[timestamps.length - 1]), 'dd.MM.yyyy');
    this.headerDateRange = start === end ? start : `${start} - ${end}`;
  }

  private extractReferenceBounds(reference: Record<string, unknown> | null): NumericReferenceBounds {
    if (!reference) {
      return {};
    }

    let refMin = this.pickNumeric(reference, ['min', 'lower', 'min_value', 'minimum', 'range_min']);
    let refMax = this.pickNumeric(reference, ['max', 'upper', 'max_value', 'maximum', 'range_max']);

    const rangeObj = this.pickObject(reference, ['range', 'bounds', 'reference_range']);
    if (rangeObj) {
      refMin = refMin ?? this.pickNumeric(rangeObj, ['min', 'lower', 'min_value', 'minimum']);
      refMax = refMax ?? this.pickNumeric(rangeObj, ['max', 'upper', 'max_value', 'maximum']);
    }

    if (refMin === undefined && refMax === undefined) {
      const typeRaw = reference['type'];
      const thresholdRaw = reference['threshold'];
      const threshold = this.toNumber(thresholdRaw);
      const type = typeof typeRaw === 'string' ? typeRaw.trim().toLowerCase() : '';
      if (threshold !== undefined) {
        if (type === 'max') {
          refMax = threshold;
        } else if (type === 'min') {
          refMin = threshold;
        }
      }
    }

    if (refMin !== undefined && refMax !== undefined && refMin > refMax) {
      [refMin, refMax] = [refMax, refMin];
    }

    return {
      ...(refMin !== undefined ? { refMin } : {}),
      ...(refMax !== undefined ? { refMax } : {}),
    };
  }

  private pickNumeric(source: Record<string, unknown>, variants: string[]): number | undefined {
    const variantSet = new Set(variants.map((key) => this.normalizeKey(key)));
    for (const [key, value] of Object.entries(source)) {
      if (!variantSet.has(this.normalizeKey(key))) {
        continue;
      }
      const parsed = this.toNumber(value);
      if (parsed !== undefined) {
        return parsed;
      }
    }
    return undefined;
  }

  private pickObject(source: Record<string, unknown>, variants: string[]): Record<string, unknown> | undefined {
    const variantSet = new Set(variants.map((key) => this.normalizeKey(key)));
    for (const [key, value] of Object.entries(source)) {
      if (!variantSet.has(this.normalizeKey(key))) {
        continue;
      }
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        return value as Record<string, unknown>;
      }
    }
    return undefined;
  }

  private normalizeKey(input: string): string {
    return input.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  }

  private toNumber(value: unknown): number | undefined {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const normalized = value.trim().replace(',', '.');
      if (!normalized) {
        return undefined;
      }
      const parsed = Number(normalized);
      return Number.isFinite(parsed) ? parsed : undefined;
    }
    return undefined;
  }

  private formatNumber(value: number): string {
    if (!Number.isFinite(value)) {
      return '-';
    }
    const rounded = Math.round(value * 100) / 100;
    if (Number.isInteger(rounded)) {
      return String(rounded);
    }
    return rounded.toFixed(2).replace(/\.?0+$/, '');
  }

  formatReferenceRangeLabel(bounds: NumericReferenceBounds): string {
    const hasMin = bounds.refMin !== undefined && bounds.refMin !== null;
    const hasMax = bounds.refMax !== undefined && bounds.refMax !== null;
    if (hasMin && hasMax) {
      return `${this.formatNumber(bounds.refMin as number)} - ${this.formatNumber(bounds.refMax as number)}`;
    }
    if (hasMin) {
      return `> ${this.formatNumber(bounds.refMin as number)}`;
    }
    if (hasMax) {
      return `< ${this.formatNumber(bounds.refMax as number)}`;
    }
    return '-';
  }

  private getNumericStatus(point: V2SeriesPointResponse | undefined): NumericStatus {
    if (!point || point.y === null || point.y === undefined) {
      return 'unknown';
    }
    if (this.hasCategoricalReference) {
      return 'unknown';
    }
    const hasRefMin = this.referenceBounds.refMin !== undefined && this.referenceBounds.refMin !== null;
    const hasRefMax = this.referenceBounds.refMax !== undefined && this.referenceBounds.refMax !== null;
    if (!hasRefMin && !hasRefMax) {
      return 'unknown';
    }
    if (hasRefMin && point.y < (this.referenceBounds.refMin as number)) {
      return 'low';
    }
    if (hasRefMax && point.y > (this.referenceBounds.refMax as number)) {
      return 'high';
    }
    return 'normal';
  }

  private getStatusLabel(status: NumericStatus): string {
    return STATUS_LABELS[this.language][status];
  }

  private getPointStatusLabel(point: V2SeriesPointResponse | undefined): string {
    if (!point || point.y === null || point.y === undefined) {
      return this.getStatusLabel('unknown');
    }
    const categoricalStatus = this.getCategoricalCategoryLabel(point.y);
    if (categoricalStatus) {
      return categoricalStatus;
    }
    return this.getStatusLabel(this.getNumericStatus(point));
  }

  private normalizeBinary(raw: string | null): BinaryCanonical {
    if (!raw) {
      return 'unknown';
    }
    const normalized = raw
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9+]/g, '');

    const positives = new Set(['positive', 'positivo', 'pos', 'reactive', 'reactivo', 'detected', 'detecto', '+']);
    const negatives = new Set(['negative', 'negativo', 'neg', 'nonreactive', 'noreactivo', 'notdetected', 'undetected', '-']);

    if (positives.has(normalized)) {
      return 'positive';
    }
    if (negatives.has(normalized)) {
      return 'negative';
    }
    return 'unknown';
  }

  private getBinaryLabel(value: BinaryCanonical): string {
    return BINARY_LABELS[this.language][value];
  }

  private getPointValueLabel(point: V2SeriesPointResponse): string {
    if (point.y !== null && point.y !== undefined) {
      const unit = this.series?.unit ? ` ${this.series.unit}` : '';
      return `${this.formatNumber(point.y)}${unit}`;
    }
    if (this.isBinary) {
      return this.getBinaryLabel(this.normalizeBinary(point.text));
    }
    if (point.text?.trim()) {
      return point.text;
    }
    return '-';
  }

  private buildReferenceAnnotations(
    labelsLength: number,
    axisBounds: { suggestedMin?: number; suggestedMax?: number; axisMin?: number; axisMax?: number },
  ): Record<string, unknown> {
    const annotations: Record<string, unknown> = {};
    if (labelsLength <= 0) {
      return annotations;
    }

    if (this.hasCategoricalReference) {
      this.categoricalReferenceBands.forEach((band, index) => {
        const yMin = band.min !== null ? band.min : axisBounds.axisMin;
        const yMax = band.max !== null ? band.max : axisBounds.axisMax;
        if (yMin === undefined || yMax === undefined) {
          return;
        }
        annotations[`catBand_${index}`] = {
          type: 'box',
          xMin: 0,
          xMax: Math.max(labelsLength - 1, 0),
          yMin,
          yMax,
          backgroundColor: band.backgroundColor,
          borderWidth: 1,
          borderColor: band.borderColor,
          drawTime: 'beforeDatasetsDraw',
          z: -10,
        };
      });
      return annotations;
    }

    if (this.referenceBounds.refMin !== undefined && this.referenceBounds.refMin !== null) {
      annotations['refMin'] = {
        type: 'line',
        yMin: this.referenceBounds.refMin,
        yMax: this.referenceBounds.refMin,
        borderColor: 'rgba(72, 187, 120, 0.9)',
        borderWidth: 2,
        borderDash: [6, 4],
      };
    }
    if (this.referenceBounds.refMax !== undefined && this.referenceBounds.refMax !== null) {
      annotations['refMax'] = {
        type: 'line',
        yMin: this.referenceBounds.refMax,
        yMax: this.referenceBounds.refMax,
        borderColor: 'rgba(239, 68, 68, 0.9)',
        borderWidth: 2,
        borderDash: [6, 4],
      };
    }
    return annotations;
  }

  private computeAxisBounds(
    points: V2SeriesPointResponse[],
  ): { suggestedMin?: number; suggestedMax?: number; axisMin?: number; axisMax?: number } {
    const numericValues = points
      .map((point) => point.y)
      .filter((value): value is number => value !== null && value !== undefined && Number.isFinite(value));
    const categoryValues = this.categoricalReferenceBands.flatMap((band) =>
      [band.min, band.max].filter((value): value is number => value !== null && value !== undefined && Number.isFinite(value)),
    );
    const allValues = [...numericValues, ...categoryValues];
    if (!allValues.length) {
      return {};
    }

    let axisMin = Math.min(...allValues);
    let axisMax = Math.max(...allValues);
    if (!Number.isFinite(axisMin) || !Number.isFinite(axisMax)) {
      return {};
    }

    if (axisMin === axisMax) {
      axisMin -= 1;
      axisMax += 1;
    }

    const range = axisMax - axisMin;
    const pad = Math.max(range * 0.1, 1);
    axisMin -= pad;
    axisMax += pad;

    if (this.hasCategoricalReference) {
      return {
        suggestedMin: axisMin,
        suggestedMax: axisMax,
        axisMin,
        axisMax,
      };
    }

    const refMin = this.referenceBounds.refMin;
    const refMax = this.referenceBounds.refMax;
    const hasRefMin = refMin !== undefined && refMin !== null;
    const hasRefMax = refMax !== undefined && refMax !== null;

    if (hasRefMin && hasRefMax) {
      const refSpan = Math.abs((refMax as number) - (refMin as number));
      const refPad = Math.max(refSpan * 0.1, 1);
      return {
        suggestedMin: Math.min(axisMin, (refMin as number) - refPad),
        suggestedMax: Math.max(axisMax, (refMax as number) + refPad),
        axisMin,
        axisMax,
      };
    }

    if (hasRefMin) {
      return {
        suggestedMin: Math.min(axisMin, (refMin as number) - 1),
        suggestedMax: axisMax,
        axisMin,
        axisMax,
      };
    }

    if (hasRefMax) {
      return {
        suggestedMin: axisMin,
        suggestedMax: Math.max(axisMax, (refMax as number) + 1),
        axisMin,
        axisMax,
      };
    }

    return {
      suggestedMin: axisMin,
      suggestedMax: axisMax,
      axisMin,
      axisMax,
    };
  }

  private extractCategoricalReferenceBands(reference: Record<string, unknown> | null): CategoricalReferenceBand[] {
    if (!reference) {
      return [];
    }
    const typeRaw = reference['type'];
    const type = typeof typeRaw === 'string' ? typeRaw.trim().toLowerCase() : '';
    if (type !== 'categorical') {
      return [];
    }
    const categoriesRaw = reference['categories'];
    if (!Array.isArray(categoriesRaw)) {
      return [];
    }
    const palette = this.getCategoricalZonePalette();

    return categoriesRaw
      .map((item, index): CategoricalReferenceBand | null => {
        if (!item || typeof item !== 'object' || Array.isArray(item)) {
          return null;
        }
        const category = item as Record<string, unknown>;
        const labelRaw = category['label'];
        const label = typeof labelRaw === 'string' && labelRaw.trim() ? labelRaw.trim() : `Category ${index + 1}`;
        let min = this.toNumber(category['min']) ?? null;
        let max = this.toNumber(category['max']) ?? null;
        if (min !== null && max !== null && min > max) {
          [min, max] = [max, min];
        }
        return {
          label,
          min,
          max,
          backgroundColor: palette.fills[index % palette.fills.length],
          borderColor: palette.border,
        };
      })
      .filter((item): item is CategoricalReferenceBand => item !== null);
  }

  private getCategoricalZonePalette(): { fills: string[]; border: string } {
    const styles = getComputedStyle(document.documentElement);
    const fallbackFills = [
      'rgba(34, 197, 94, 0.14)',
      'rgba(59, 130, 246, 0.14)',
      'rgba(245, 158, 11, 0.14)',
      'rgba(239, 68, 68, 0.14)',
      'rgba(168, 85, 247, 0.14)',
    ];
    const fills = [
      this.readCssVar(styles, '--chart-zone-low'),
      this.readCssVar(styles, '--chart-zone-mid'),
      this.readCssVar(styles, '--chart-zone-high'),
      this.readCssVar(styles, '--chart-zone-alt-1'),
      this.readCssVar(styles, '--chart-zone-alt-2'),
    ].map((value, index) => value ?? fallbackFills[index]);

    const border = this.readCssVar(styles, '--chart-zone-border') ?? 'rgba(118, 138, 182, 0.45)';
    return { fills, border };
  }

  private getCategoricalCategoryLabel(value: number): string | null {
    if (!this.hasCategoricalReference || !Number.isFinite(value)) {
      return null;
    }
    for (const band of this.categoricalReferenceBands) {
      const minOk = band.min === null || value >= band.min;
      const maxOk = band.max === null || value <= band.max;
      if (minOk && maxOk) {
        return band.label;
      }
    }
    return this.getStatusLabel('unknown');
  }
}
