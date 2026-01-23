import { Component, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { BaseChartDirective } from 'ng2-charts';
import { Subscription } from 'rxjs';
import Chart from 'chart.js/auto';
import zoomPlugin from 'chartjs-plugin-zoom';
import { ChartConfiguration, ScatterDataPoint, ScriptableContext, TooltipItem } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { format } from 'date-fns';

import { DoctorService } from '../../../../core/services/doctor.service';
import { AnalysisSummary, CategoricalSeriesPoint, MetricSeriesPoint, MetricSeriesResponse } from '../../../../core/models/analysis.model';
import { DoctorNote } from '../../../../core/models/doctor.model';

Chart.register(zoomPlugin);

const HIDDEN_METRICS = new Set([
  'RESPONSABLE DE SUCURSAL',
  'RESPONSABLE DE LABORATORIO',
  'OTROS',
  'OTROS:',
  'CED.PROF',
  'PAG.',
]);

// Reference range plugin (same as in patient charts)
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

    // Get global min and max (use first point's values as baseline)
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

    // Optional: Draw filled band between min and max (subtle background)
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

// Safe global registration (idempotent in Chart.js)
Chart.register(normBandPlugin);

@Component({
  selector: 'app-doctor-patient-detail-page',
  standalone: false,
  templateUrl: './doctor-patient-detail-page.component.html',
  styleUrls: ['./doctor-patient-detail-page.component.scss'],
})
export class DoctorPatientDetailPageComponent implements OnInit, OnDestroy {
  private readonly doctorService = inject(DoctorService);
  private readonly route = inject(ActivatedRoute);

  @ViewChild(BaseChartDirective) chart?: BaseChartDirective;

  patientId = '';
  patientName = '';
  metricOptions: string[] = [];
  filteredMetrics: string[] = [];
  showMetricList = false;
  metricFilter = '';
  selectedMetric = '';
  analyses: AnalysisSummary[] = [];
  analysesLoading = true;
  loading = true;
  series: MetricSeriesPoint[] = [];
  seriesType: MetricSeriesResponse['series_type'] = 'numeric';
  categoricalPoints: CategoricalSeriesPoint[] = [];
  seriesStage?: string | null;
  seriesStageLabel?: string | null;
  errorMessage = '';
  private sub?: Subscription;

  notes: DoctorNote[] = [];
  notesLoading = false;
  newNote = '';
  noteError = '';
  selectedPoint = '';
  private noteMap = new Map<number, DoctorNote[]>();

  chartData: ChartConfiguration['data'] = { datasets: [] };
  chartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: 'time',
        time: { unit: 'day', tooltipFormat: 'dd MMM yyyy' },
        title: { display: true, text: 'Date' },
        ticks: {
          color: 'rgba(232, 236, 248, 0.55)',
          callback: (value) => {
            const v = typeof value === 'number' ? value : Number(value);
            if (!Number.isFinite(v)) return '';
            try {
              return format(new Date(v), 'dd MMM yyyy');
            } catch {
              return '';
            }
          },
        },
        grid: { color: 'rgba(232, 236, 248, 0.06)', lineWidth: 0.5 },
      },
      y: {
        title: {
          display: false,  // Will be updated dynamically with unit in updateChart()
          text: '',
        },
        ticks: { color: 'rgba(232, 236, 248, 0.55)' },
        grid: { color: 'rgba(232, 236, 248, 0.05)', lineWidth: 0.5 },
      },
    },
    plugins: {
      tooltip: {
        callbacks: {
          afterLabel: (context: TooltipItem<'scatter'>) => this.tooltipNotes(context),
        },
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
        ranges: [],
        fillStyle: 'rgba(118, 168, 255, 0.08)',
      } as any,  // Custom plugin type
    } as any,
  };

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe((params) => {
      this.patientId = params.get('id') ?? '';
      if (this.patientId) {
        this.loadPatientIdentity();
        this.loadMetrics();
        this.loadNotes();
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  onMetricChange(metric: string): void {
    if (this.selectedMetric === metric) {
      return;
    }
    this.selectedMetric = metric;
    this.loadSeries();
  }

  private loadMetrics(): void {
    this.loading = true;
    this.errorMessage = '';
    this.metricOptions = [];
    this.analysesLoading = true;

    this.doctorService.getAnalyses(this.patientId).subscribe({
      next: (analyses) => {
        this.analyses = analyses ?? [];
        const names = new Set<string>();
        (analyses ?? []).forEach((analysis: any) => {
          (analysis.metrics ?? []).forEach((m: any) => {
            const name = (m?.name ?? '').trim();
            if (name) {
              const normalized = name.toUpperCase();
              if (HIDDEN_METRICS.has(normalized)) {
                return;
              }
              names.add(name);
            }
          });
        });

        this.metricOptions = Array.from(names).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
        this.filteredMetrics = [...this.metricOptions];
        this.analysesLoading = false;

        if (!this.metricOptions.length) {
          this.errorMessage = 'No metrics available for this patient yet.';
          this.loading = false;
          return;
        }

        this.selectedMetric = this.metricOptions[0];
        this.loadSeries();
      },
      error: (err) => {
        this.analyses = [];
        this.analysesLoading = false;
        this.errorMessage = err?.error?.detail ?? 'Failed to load metrics list.';
        this.loading = false;
      },
    });
  }

  private loadPatientIdentity(): void {
    this.doctorService.listPatients().subscribe({
      next: (response) => {
        const match = response?.patients?.find((p) => `${p.patient_id}` === `${this.patientId}`);
        if (match) {
          this.patientName = match.full_name || match.email || '';
        }
      },
    });
  }

  toggleMetricList(): void {
    this.showMetricList = !this.showMetricList;
    if (this.showMetricList) {
      this.metricFilter = '';
      this.filteredMetrics = [...this.metricOptions];
      setTimeout(() => {
        const el = document.querySelector<HTMLInputElement>('#metric-filter');
        el?.focus();
      }, 0);
    }
  }

  filterMetrics(term: string): void {
    this.metricFilter = term;
    const t = term.toLowerCase();
    this.filteredMetrics = this.metricOptions.filter((m) => m.toLowerCase().includes(t));
  }

  selectMetric(metric: string): void {
    if (this.selectedMetric === metric) {
      this.showMetricList = false;
      return;
    }
    this.selectedMetric = metric;
    this.showMetricList = false;
    this.rebuildNoteMap();
    this.loadSeries();
  }

  loadNotes(): void {
    if (!this.patientId) {
      return;
    }
    this.notesLoading = true;
    this.noteError = '';
    this.doctorService.getNotes(this.patientId).subscribe({
      next: (notes) => {
        this.notes = notes ?? [];
        this.rebuildNoteMap();
        this.chart?.update();
        this.notesLoading = false;
      },
      error: (err) => {
        this.noteError = err?.error?.detail ?? 'Failed to load notes.';
        this.notesLoading = false;
      },
    });
  }

  get notesForMetric(): DoctorNote[] {
    return this.notes.filter((n) => !n.metric_name || n.metric_name === this.selectedMetric);
  }

  get pointOptions(): { value: string; label: string }[] {
    if (this.seriesType === 'categorical') {
      return this.categoricalPoints.map((p) => {
        const ts = new Date(p.date);
        return { value: p.date, label: format(ts, 'dd MMM yyyy') };
      });
    }
    return this.series.map((p) => {
      const ts = new Date(p.t);
      return { value: p.t, label: format(ts, 'dd MMM yyyy, HH:mm') };
    });
  }

  addNote(): void {
    const text = this.newNote.trim();
    if (!text || !this.patientId || !this.selectedMetric || !this.selectedPoint) {
      return;
    }
    this.noteError = '';
    this.doctorService.addNote(this.patientId, text, this.selectedMetric, this.selectedPoint).subscribe({
      next: (note) => {
        this.notes = [note, ...this.notes];
        this.newNote = '';
        this.rebuildNoteMap();
        this.chart?.update();
      },
      error: (err) => {
        this.noteError = err?.error?.detail ?? 'Failed to add note.';
      },
    });
  }

  private loadSeries(): void {
    if (!this.patientId || !this.selectedMetric) {
      this.loading = false;
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    this.doctorService.getSeries(this.patientId, this.selectedMetric).subscribe({
      next: (seriesResponse) => {
        this.seriesType = seriesResponse?.series_type ?? 'numeric';
        this.seriesStage = seriesResponse?.stage ?? null;
        this.seriesStageLabel = seriesResponse?.stage_label ?? null;

        if (this.seriesType === 'categorical') {
          this.series = [];
          this.categoricalPoints = this.normalizeCategorical(seriesResponse?.points ?? []);
          this.selectedPoint = this.categoricalPoints.length ? this.categoricalPoints[this.categoricalPoints.length - 1].date : '';
          this.chartData = { datasets: [] };
        } else {
          this.categoricalPoints = [];
          this.series = this.normalizeNumeric(seriesResponse?.points ?? seriesResponse);
          this.selectedPoint = this.series.length ? this.series[this.series.length - 1].t : '';
          this.updateChart();
        }

        this.rebuildNoteMap();
        this.chart?.update();
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'Failed to load time series.';
        this.loading = false;
      },
    });
  }

  private normalizeNumeric(raw: unknown): MetricSeriesPoint[] {
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

  private normalizeCategorical(raw: unknown): CategoricalSeriesPoint[] {
    const asArray: any[] = Array.isArray(raw) ? raw : Object.values(raw ?? {});
    const normalized = asArray
      .map((point) => {
        const dateValue = (point?.date ?? point?.t ?? point?.taken_at ?? point?.created_at) as string | undefined;
        const valueText = (point?.value_text ?? point?.value) as string | undefined;
        if (!dateValue || !valueText) {
          return null;
        }
        const ts = Date.parse(dateValue);
        if (!Number.isFinite(ts)) {
          return null;
        }
        return {
          date: new Date(ts).toISOString(),
          value_text: valueText,
        } as CategoricalSeriesPoint;
      })
      .filter((point): point is CategoricalSeriesPoint => point !== null);

    return normalized.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }

  private calculateYAxisMin(ranges: MetricSeriesPoint[]): number | undefined {
    if (!ranges.length) return undefined;

    const values = ranges.map(p => p.y).filter(v => v != null);
    const refMins = ranges.map(p => p.refMin).filter(v => v != null) as number[];

    if (!values.length) return undefined;

    const dataMin = Math.min(...values);
    const refMin = refMins.length ? Math.min(...refMins) : null;

    const minValue = refMin != null ? Math.min(dataMin, refMin) : dataMin;
    return minValue * 0.9;  // 10% padding
  }

  private calculateYAxisMax(ranges: MetricSeriesPoint[]): number | undefined {
    if (!ranges.length) return undefined;

    const values = ranges.map(p => p.y).filter(v => v != null);
    const refMaxs = ranges.map(p => p.refMax).filter(v => v != null) as number[];

    if (!values.length) return undefined;

    const dataMax = Math.max(...values);
    const refMax = refMaxs.length ? Math.max(...refMaxs) : null;

    const maxValue = refMax != null ? Math.max(dataMax, refMax) : dataMax;
    return maxValue * 1.1;  // 10% padding
  }

  private updateChart(): void {
    const dataPoints: ScatterDataPoint[] = this.series.map((point) => ({
      x: new Date(point.t).getTime(),
      y: point.y,
    }));

    // Extract unit from first point (all points should have the same unit)
    const unit = this.series.length > 0 && this.series[0]?.unit ? this.series[0].unit : null;
    const yAxisTitle = unit || '';

    this.chartData = {
      datasets: [
        {
          label: this.selectedMetric,
          data: dataPoints,
          borderColor: '#76a8ff',
          backgroundColor: 'rgba(118, 168, 255, 0.25)',
          tension: 0.25,
          showLine: true,
          spanGaps: true,
          pointRadius: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => (this.hasNoteAtContext(ctx) ? 6 : 4),
          pointHoverRadius: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => (this.hasNoteAtContext(ctx) ? 8 : 6),
          pointBackgroundColor: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => {
            if (this.hasNoteAtContext(ctx)) {
              return 'rgba(252, 211, 77, 0.95)';
            }
            const stage = this.series[ctx.dataIndex]?.stage;
            return stage ? this.getStageColor(stage) : 'rgba(118, 168, 255, 0.25)';
          },
          pointBorderColor: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => {
            if (this.hasNoteAtContext(ctx)) {
              return '#fde68a';
            }
            const stage = this.series[ctx.dataIndex]?.stage;
            return stage ? this.getStageColor(stage) : '#76a8ff';
          },
          pointBorderWidth: (ctx: ScriptableContext<'scatter'> | ScriptableContext<'line'>) => (this.hasNoteAtContext(ctx) ? 3 : 1),
          fill: false,
        },
      ],
    };

    // Update Y-axis title and range with unit
    if (this.chartOptions?.scales?.['y']) {
      const yScale = this.chartOptions.scales['y'] as any;
      if (yScale) {
        yScale.title = {
          display: !!yAxisTitle,
          text: yAxisTitle,
          color: 'rgba(232, 236, 248, 0.75)',
          font: {
            size: 12,
            family: 'Inter, system-ui, sans-serif',
            weight: 500,
          },
          padding: { top: 0, bottom: 8 },
        };
        // Auto-adjust Y-axis range to include reference values
        yScale.min = this.calculateYAxisMin(this.series);
        yScale.max = this.calculateYAxisMax(this.series);
      }
    }

    // Update reference range plugin with series data
    const plugins = this.chartOptions?.plugins as any;
    if (plugins?.normBand) {
      plugins.normBand.ranges = this.series;
    }

    // Debug: log reference values
    const validRefs = this.series.filter(p => p.refMin != null && p.refMax != null);
    if (validRefs.length > 0) {
      console.log('[Chart] Reference values found:', {
        count: validRefs.length,
        refMin: validRefs[0].refMin,
        refMax: validRefs[0].refMax,
        yAxisMin: this.calculateYAxisMin(this.series),
        yAxisMax: this.calculateYAxisMax(this.series),
      });
    } else {
      console.log('[Chart] No reference values found in series:', this.series);
    }

    this.chart?.update();
  }

  private rebuildNoteMap(): void {
    this.noteMap.clear();
    if (!this.selectedMetric) {
      return;
    }
    this.notes
      .filter((n) => !n.metric_name || n.metric_name === this.selectedMetric)
      .forEach((note) => {
        if (!note.metric_time) {
          return;
        }
        const ts = new Date(note.metric_time).getTime();
        if (!Number.isFinite(ts)) {
          return;
        }
        const arr = this.noteMap.get(ts) ?? [];
        arr.push(note);
        this.noteMap.set(ts, arr);
      });
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
  private tooltipNotes(context: TooltipItem<'scatter'>): string | string[] {
    const timestamp = this.extractTimestamp(context.parsed?.x);
    if (timestamp === null) {
      return '';
    }
    const stageLabel = this.series[context.dataIndex]?.stage_label;
    const notes = this.noteMap.get(timestamp) ?? [];
    const stageLines = stageLabel ? [stageLabel] : [];
    if (!notes.length) {
      return stageLines;
    }
    const noteLines = notes.map((note) => {
      const ts = note.metric_time ? format(new Date(note.metric_time), 'dd MMM yyyy, HH:mm') : '';
      return `* ${note.text}${ts ? ` (${ts})` : ''}`;
    });
    return [...stageLines, ...noteLines];
  }

  private getStageColor(stage: string): string {
    const normalized = stage.toUpperCase();
    const colors: Record<string, string> = {
      G1: '#5ad670',
      G2: '#9ad66a',
      G3A: '#f2c94c',
      G3B: '#f2994a',
      G4: '#eb5757',
      G5: '#b71c1c',
    };
    return colors[normalized] ?? '#76a8ff';
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
