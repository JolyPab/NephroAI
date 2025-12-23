import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import Chart from 'chart.js/auto';
import zoomPlugin from 'chartjs-plugin-zoom';
import { ChartConfiguration, ChartDataset, TooltipModel, ScatterDataPoint, ScriptableContext } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { format } from 'date-fns';

import { PatientService } from '../../../../core/services/patient.service';
import { AnalysisSummary, MetricSeriesPoint } from '../../../../core/models/analysis.model';
import { DoctorNote } from '../../../../core/models/doctor.model';

Chart.register(zoomPlugin);

interface NormBandPluginOptions {
  ranges: MetricSeriesPoint[];
  fillStyle: string;
}

const normBandPlugin = {
  id: 'normBand',
  beforeDatasetsDraw(chart: Chart, _args: unknown, options?: NormBandPluginOptions) {
    const ranges = options?.ranges ?? [];
    if (!ranges.length) {
      return;
    }

    const meta = chart.getDatasetMeta(0);
    if (!meta?.data?.length) {
      return;
    }

    const { ctx, scales, chartArea } = chart;
    const yScale = scales['y'];
    const xScale = scales['x'];

    if (!yScale || !xScale || !chartArea) {
      return;
    }

    // Find global min and max reference values across all points
    const validRefs = ranges
      .filter((point) => 
        point?.refMin !== null && 
        point?.refMin !== undefined && 
        point?.refMax !== null && 
        point?.refMax !== undefined
      )
      .map((point) => ({ refMin: point.refMin!, refMax: point.refMax! }));

    if (!validRefs.length) {
      return;
    }

    // Get global min and max (use first point's values as baseline, or average)
    // For simplicity, use the first valid point's ref values (they should be consistent)
    const globalRefMin = validRefs[0].refMin;
    const globalRefMax = validRefs[0].refMax;

    // Draw horizontal dashed lines for min and max reference values
    ctx.save();
    ctx.strokeStyle = 'rgba(118, 168, 255, 0.85)';  // More visible
    ctx.setLineDash([8, 4]);
    ctx.lineWidth = 2;  // Thicker line

    // Draw min reference line (horizontal across entire chart)
    const yMin = yScale.getPixelForValue(globalRefMin);
    if (Number.isFinite(yMin)) {
      ctx.beginPath();
      ctx.moveTo(chartArea.left, yMin);
      ctx.lineTo(chartArea.right, yMin);
      ctx.stroke();
    }

    // Draw max reference line (horizontal across entire chart)
    const yMax = yScale.getPixelForValue(globalRefMax);
    if (Number.isFinite(yMax)) {
      ctx.beginPath();
      ctx.moveTo(chartArea.left, yMax);
      ctx.lineTo(chartArea.right, yMax);
      ctx.stroke();
    }

    ctx.restore();

    // Keep the existing band visualization (optional - can remove if only want lines)
    const segments = meta.data
      .map((element, index) => {
        const point = ranges[index];
        if (!point || point.refMin === null || point.refMax === null || point.refMin === undefined || point.refMax === undefined) {
          return null;
        }
        const pointElement = element as { x: number };
        const x = pointElement.x;
        const yMinPix = yScale.getPixelForValue(point.refMin);
        const yMaxPix = yScale.getPixelForValue(point.refMax);
        if (!Number.isFinite(x) || !Number.isFinite(yMinPix) || !Number.isFinite(yMaxPix)) {
          return null;
        }
        return { x, yMin: yMinPix, yMax: yMaxPix };
      })
      .filter((seg): seg is { x: number; yMin: number; yMax: number } => seg !== null);

    if (segments.length) {
      // Draw filled band between min and max (subtle background)
    ctx.save();
    ctx.beginPath();
      ctx.fillStyle = options?.fillStyle ?? 'rgba(118, 168, 255, 0.08)';

    ctx.moveTo(segments[0].x, segments[0].yMax);
    segments.forEach((seg) => ctx.lineTo(seg.x, seg.yMax));
    for (let i = segments.length - 1; i >= 0; i--) {
      const seg = segments[i];
      ctx.lineTo(seg.x, seg.yMin);
    }
    ctx.closePath();
    ctx.fill();
    ctx.restore();
    }
  },
};

Chart.register(normBandPlugin);

type TrendChartConfig = ChartConfiguration<'scatter', ScatterDataPoint[]>;

const toScatterPoint = (point: MetricSeriesPoint): ScatterDataPoint => ({
  x: new Date(point.t).getTime(),
  y: point.y,
});

// Hide non-metric garbage that may slip from PDFs
const HIDDEN_METRICS = new Set([
  'RESPONSABLE DE SUCURSAL',
  'OTROS',
  'OTROS:',
]);

@Component({
  selector: 'app-patient-charts-page',
  standalone: false,
  templateUrl: './charts-page.component.html',
  styleUrls: ['./charts-page.component.scss'],
})
export class PatientChartsPageComponent implements OnInit {
  private readonly patientService = inject(PatientService);

  @ViewChild(BaseChartDirective) chart?: BaseChartDirective;

  analyses: AnalysisSummary[] = [];
  metricNames: string[] = [];
  selectedMetric = '';
  metricFilter = '';
  isLoading = true;
  series: MetricSeriesPoint[] = [];
  errorMessage = '';
  noteMap = new Map<number, DoctorNote[]>();

  chartData: TrendChartConfig['data'] = { datasets: [] };

  chartOptions: TrendChartConfig['options'] = {};

  ngOnInit(): void {
    this.chartOptions = this.buildBaseOptions();

    this.patientService.getAnalyses().subscribe({
      next: (analyses) => {
        this.analyses = analyses ?? [];
        this.metricNames = Array.from(
          new Set(
            this.analyses
              .flatMap((analysis) => analysis.metrics?.map((metric) => metric.name) ?? [])
              .filter((name) => {
                if (!name) return false;
                const normalized = name.trim().toUpperCase();
                return !HIDDEN_METRICS.has(normalized);
              })
          ),
        ).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
        this.selectedMetric = this.metricNames[0] ?? '';
        this.isLoading = false;
        if (this.selectedMetric) {
          this.loadSeries();
        }
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'Failed to load metrics list.';
        this.isLoading = false;
      },
    });
  }

  onMetricChange(metric: string): void {
    if (this.selectedMetric === metric) {
      return;
    }
    this.selectedMetric = metric;
    this.loadSeries();
  }

  trackByName(_: number, item: string): string {
    return item;
  }

  get filteredMetrics(): string[] {
    const term = this.metricFilter.trim().toLowerCase();
    if (!term) {
      return this.metricNames;
    }
    return this.metricNames.filter((name) => name.toLowerCase().includes(term));
  }

  private normalizeSeries(raw: unknown): MetricSeriesPoint[] {
    const asArray: any[] = Array.isArray(raw) ? raw : Object.values(raw ?? {});
    const normalized = asArray
      .map((p) => {
        const taken =
          (p?.taken_at as string | undefined) ??
          (p?.t as string | undefined) ??
          (p?.date as string | undefined) ??
          (p?.created_at as string | undefined);
        const ts = taken ? Date.parse(taken) : NaN;
        if (!Number.isFinite(ts)) {
          return null;
        }
        const yRaw = (p?.y ?? p?.value) as unknown;
        const yNum =
          typeof yRaw === 'string'
            ? Number(yRaw.replace(',', '.'))
            : typeof yRaw === 'number'
              ? yRaw
              : null;
        if (yNum === null || !Number.isFinite(yNum)) {
          return null;
        }

        const refMinRaw = (p as any)?.refMin ?? (p as any)?.ref_min;
        const refMaxRaw = (p as any)?.refMax ?? (p as any)?.ref_max;
        const refMin = typeof refMinRaw === 'string' ? Number(refMinRaw.replace(',', '.')) : refMinRaw;
        const refMax = typeof refMaxRaw === 'string' ? Number(refMaxRaw.replace(',', '.')) : refMaxRaw;

        return {
          ...(p as object),
          t: new Date(ts).toISOString(),
          y: yNum,
          refMin: Number.isFinite(refMin as number) ? (refMin as number) : undefined,
          refMax: Number.isFinite(refMax as number) ? (refMax as number) : undefined,
        } as MetricSeriesPoint;
      })
      .filter((p): p is MetricSeriesPoint => p !== null);

    return normalized.sort((a, b) => new Date(a.t).getTime() - new Date(b.t).getTime());
  }

  private loadSeries(): void {
    if (!this.selectedMetric) {
      this.series = [];
      this.chartData = { datasets: [] };
      this.chartOptions = this.buildBaseOptions();
      return;
    }
    this.isLoading = true;
    this.patientService.getSeries(this.selectedMetric).subscribe({
      next: (series) => {
        this.series = this.normalizeSeries(series);
        this.updateChart();
        this.loadNotesForMetric(this.selectedMetric);
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'Failed to load time series.';
        this.isLoading = false;
      },
    });
  }

  private loadNotesForMetric(metric: string): void {
    this.noteMap.clear();
    this.patientService.getDoctorNotes(metric).subscribe({
      next: (notes) => {
        (notes ?? []).forEach((note) => {
          if (!note.metric_time) return;
          const ts = new Date(note.metric_time).getTime();
          if (!Number.isFinite(ts)) return;
          const arr = this.noteMap.get(ts) ?? [];
          arr.push(note);
          this.noteMap.set(ts, arr);
        });
        this.chart?.update();
      },
    });
  }

  private updateChart(): void {
    const dataPoints: ScatterDataPoint[] = this.series.map(toScatterPoint);

    const datasets: ChartDataset<'scatter', ScatterDataPoint[]>[] = [
      {
        label: this.selectedMetric,
        data: dataPoints,
        borderColor: 'rgba(118, 168, 255, 0.85)',
        backgroundColor: 'transparent',
        borderWidth: 3,
        tension: 0.45,
        cubicInterpolationMode: 'monotone',
        spanGaps: true,
        showLine: true,
        fill: false,
        pointRadius: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => (this.hasNoteAtContext(ctx) ? 7 : 5),
        pointHoverRadius: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => (this.hasNoteAtContext(ctx) ? 9 : 7),
        pointBackgroundColor: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) =>
          this.hasNoteAtContext(ctx) ? 'rgba(252, 211, 77, 0.95)' : 'rgba(118, 168, 255, 0.95)',
        pointBorderColor: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) =>
          this.hasNoteAtContext(ctx) ? 'rgba(255, 255, 255, 0.95)' : 'rgba(255, 255, 255, 0.9)',
        pointBorderWidth: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => (this.hasNoteAtContext(ctx) ? 3 : 2),
      },
    ];

    this.chartData = { datasets };
    this.chartOptions = this.buildBaseOptions(this.series);

    this.chart?.update();
  }

  private calculateYAxisMin(ranges: MetricSeriesPoint[]): number | undefined {
    if (!ranges.length) return undefined;
    
    const values = ranges.map(p => p.y).filter(v => v != null);
    const refMins = ranges.map(p => p.refMin).filter(v => v != null) as number[];
    
    if (!values.length) return undefined;
    
    const dataMin = Math.min(...values);
    const refMin = refMins.length ? Math.min(...refMins) : null;
    
    // Use the minimum of data and reference, with 10% padding below
    const minValue = refMin != null ? Math.min(dataMin, refMin) : dataMin;
    return this.cleanAxisValue(minValue * 0.9);  // 10% padding
  }

  private calculateYAxisMax(ranges: MetricSeriesPoint[]): number | undefined {
    if (!ranges.length) return undefined;
    
    const values = ranges.map(p => p.y).filter(v => v != null);
    const refMaxs = ranges.map(p => p.refMax).filter(v => v != null) as number[];
    
    if (!values.length) return undefined;
    
    const dataMax = Math.max(...values);
    const refMax = refMaxs.length ? Math.max(...refMaxs) : null;
    
    // Use the maximum of data and reference, with 10% padding above
    const maxValue = refMax != null ? Math.max(dataMax, refMax) : dataMax;
    return this.cleanAxisValue(maxValue * 1.1);  // 10% padding
  }

  private cleanAxisValue(value?: number): number | undefined {
    if (value === undefined || value === null) return undefined;
    if (!Number.isFinite(value)) return undefined;
    // Trim floating artifacts like 220.00000000000003
    return parseFloat(value.toFixed(3));
  }

  private getCssVar(name: string, fallback: string): string {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  private buildBaseOptions(ranges: MetricSeriesPoint[] = []): TrendChartConfig['options'] {
    const externalTooltip = this.externalTooltipHandler.bind(this);
    const text = this.getCssVar('--text', 'rgba(30, 34, 45, 0.85)');
    const textDim = this.getCssVar('--text-dim', 'rgba(30, 34, 45, 0.55)');
    
    // Extract unit from first point (all points should have the same unit)
    const unit = ranges.length > 0 && ranges[0]?.unit ? ranges[0].unit : null;
    const yAxisTitle = unit || '';
    
    // Debug: log reference values
    const validRefs = ranges.filter(p => p.refMin != null && p.refMax != null);
    if (validRefs.length > 0) {
      console.log('[Chart] Reference values found:', {
        count: validRefs.length,
        refMin: validRefs[0].refMin,
        refMax: validRefs[0].refMax,
        yAxisMin: this.calculateYAxisMin(ranges),
        yAxisMax: this.calculateYAxisMax(ranges),
      });
    } else {
      console.log('[Chart] No reference values found in ranges:', ranges);
    }
    
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 260, easing: 'easeOutQuad' },
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'day',
            displayFormats: { day: 'dd.MM.yyyy' },
            tooltipFormat: 'dd.MM.yyyy',
          },
          grid: { color: 'rgba(232, 236, 248, 0.12)', lineWidth: 0.5 },
          ticks: {
            color: textDim,
            maxRotation: 0,
            font: { size: 11, family: 'Inter, system-ui, sans-serif' },
            callback: (value) => {
              const v = typeof value === 'number' ? value : Number(value);
              if (!Number.isFinite(v)) return '';
              try {
                return format(new Date(v), 'dd.MM.yyyy');
              } catch {
                return '';
              }
            },
          },
        },
        y: {
          title: {
            display: !!yAxisTitle,
            text: yAxisTitle,
            color: text,
            font: {
              size: 12,
              family: 'Inter, system-ui, sans-serif',
              weight: 500,
            },
            padding: { top: 0, bottom: 8 },
          },
          ticks: {
            color: textDim,
            padding: 6,
            font: { size: 11, family: 'Inter, system-ui, sans-serif' },
            callback: (value) => {
              const v = typeof value === 'number' ? value : Number(value);
              if (!Number.isFinite(v)) return '';
              const rounded = parseFloat(v.toFixed(2));
              // Hide "-0" artifacts
              return Math.abs(rounded) === 0 ? '0' : rounded.toString();
            },
          },
          grid: { color: 'rgba(232, 236, 248, 0.05)', lineWidth: 0.5 },
          border: { display: false },
          // Automatically adjust Y-axis range to include reference values
          min: this.calculateYAxisMin(ranges),
          max: this.calculateYAxisMax(ranges),
        },
      },
      elements: {
        point: {
          hoverBorderWidth: 2,
        },
      },
      plugins: {
        legend: {
          labels: {
            color: text,
            font: { family: 'Inter, system-ui, sans-serif', size: 12 },
            usePointStyle: true,
          },
        },
        tooltip: {
          enabled: false,
          external: externalTooltip,
        },
        zoom: {
          pan: {
            enabled: true,
            mode: 'xy',  // Allow panning on both X and Y axes
          },
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: 'xy',  // Allow zooming on both X and Y axes
          },
        },
        normBand: {
          ranges,
          fillStyle: 'rgba(118, 168, 255, 0.12)',
        },
      },
    } as TrendChartConfig['options'];
  }

  private externalTooltipHandler(context: { chart: Chart; tooltip: TooltipModel<'scatter'> }) {
    const { chart, tooltip } = context;
    let tooltipEl = chart.canvas.parentNode?.querySelector<HTMLDivElement>('.chartjs-tooltip');

    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.className = 'chartjs-tooltip glass glass-strong';
      tooltipEl.style.position = 'absolute';
      tooltipEl.style.pointerEvents = 'none';
      tooltipEl.style.transition = 'opacity 120ms ease';
      chart.canvas.parentNode?.appendChild(tooltipEl);
    }

    if (tooltip.opacity === 0) {
      tooltipEl.style.opacity = '0';
      return;
    }

    if (tooltip.body) {
      const title = tooltip.title?.[0] ?? '';
      const bodyLines: string[] = [];
      tooltip.body.forEach((bodyItem: { lines: string[] }) => bodyLines.push(...bodyItem.lines));
      const notesHtml = this.buildNotesHtml(tooltip);
      tooltipEl.innerHTML = `
        <div class="tooltip-title">${title}</div>
        ${bodyLines
          .map(
            (line: string) =>
              `<div class="tooltip-row">
                <span>${line}</span>
              </div>`,
          )
          .join('')}
        ${notesHtml}
      `;
    }

    const { offsetLeft: positionX, offsetTop: positionY } = chart.canvas;
    tooltipEl.style.opacity = '1';

    const parent = chart.canvas.parentElement;
    const parentWidth = parent?.clientWidth ?? window.innerWidth;
    const parentHeight = parent?.clientHeight ?? window.innerHeight;
    const tooltipWidth = tooltipEl.offsetWidth || 180;
    const tooltipHeight = tooltipEl.offsetHeight || 60;

    const rawLeft = positionX + tooltip.caretX + 12;
    const rawTop = positionY + tooltip.caretY + 12;

    const padding = 8;
    const clampedLeft = Math.min(
      parentWidth - tooltipWidth - padding,
      Math.max(padding, rawLeft)
    );
    const clampedTop = Math.min(
      parentHeight - tooltipHeight - padding,
      Math.max(padding, rawTop)
    );

    tooltipEl.style.left = `${clampedLeft}px`;
    tooltipEl.style.top = `${clampedTop}px`;
  }

  private buildNotesHtml(tooltip: TooltipModel<'scatter'>): string {
    const dp = tooltip.dataPoints?.[0];
    if (!dp) return '';
    const x = (dp.parsed as any)?.x;
    if (!Number.isFinite(x)) return '';
    const notes = this.noteMap.get(x);
    if (!notes || !notes.length) return '';
    const items = notes
      .map((n) => {
        const ts = n.metric_time ? format(new Date(n.metric_time), 'dd MMM yyyy, HH:mm') : '';
        const meta = [ts, n.doctor_email].filter(Boolean).join(' • ');
        return `<div class="tooltip-row note-row"><span>${n.text}</span>${
          meta ? `<span class="note-meta">${meta}</span>` : ''
        }</div>`;
      })
      .join('');
    return `<div class="tooltip-notes">${items}</div>`;
  }

  private hasNoteAtContext(ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>): boolean {
    const timestamp = this.extractTimestamp(
      (ctx as ScriptableContext<'scatter'>).parsed?.x ??
        (ctx.raw as ScatterDataPoint | undefined)?.x ??
        ctx.raw
    );
    if (timestamp === null) {
      return false;
    }
    return this.noteMap.has(timestamp);
  }

  private extractTimestamp(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (value instanceof Date) {
      const ts = value.getTime();
      return Number.isFinite(ts) ? ts : null;
    }
    if (typeof value === 'string') {
      const ts = Date.parse(value);
      return Number.isFinite(ts) ? ts : null;
    }
    return null;
  }
}
