import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';

import { AnalysisSummary, MetricBrief } from '../../../core/models/analysis.model';
import { GlassCardComponent } from '../glass-card/glass-card.component';
import { GlassButtonDirective } from '../glass-button/glass-button.directive';

@Component({
  selector: 'app-latest-report-summary',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule, GlassCardComponent, GlassButtonDirective],
  templateUrl: './latest-report-summary.component.html',
  styleUrls: ['./latest-report-summary.component.scss'],
})
export class LatestReportSummaryComponent implements OnChanges {
  @Input() analyses: AnalysisSummary[] = [];
  @Input() showChartsButton = true;
  @Input() showEmptyState = true;

  latestAnalysis: AnalysisSummary | null = null;
  summaryMetrics: SummaryMetric[] = [];
  metricsCount = 0;
  sourceLabel: string | null = null;

  ngOnChanges(): void {
    this.latestAnalysis = this.pickLatestAnalysis(this.analyses ?? []);
    if (!this.latestAnalysis) {
      this.summaryMetrics = [];
      this.metricsCount = 0;
      this.sourceLabel = null;
      return;
    }

    this.summaryMetrics = this.buildSummaryMetrics(this.latestAnalysis.metrics ?? []);
    const countFromPayload = this.latestAnalysis.metrics_count;
    this.metricsCount =
      typeof countFromPayload === 'number' && Number.isFinite(countFromPayload)
        ? countFromPayload
        : this.latestAnalysis.metrics?.length ?? 0;
    this.sourceLabel = this.getSourceLabel(this.latestAnalysis);
  }

  latestDate(analysis: AnalysisSummary | null): string | null {
    if (!analysis) {
      return null;
    }
    return analysis.date || analysis.taken_at || analysis.created_at || null;
  }

  private pickLatestAnalysis(analyses: AnalysisSummary[]): AnalysisSummary | null {
    if (!analyses.length) {
      return null;
    }
    const sorted = [...analyses].sort((a, b) => this.getAnalysisTimestamp(b) - this.getAnalysisTimestamp(a));
    return sorted[0] ?? null;
  }

  private getAnalysisTimestamp(analysis: AnalysisSummary): number {
    const candidate = analysis.date || analysis.taken_at || analysis.created_at || '';
    const ts = Date.parse(candidate ?? '');
    return Number.isFinite(ts) ? ts : 0;
  }

  private buildSummaryMetrics(metrics: MetricBrief[]): SummaryMetric[] {
    if (!metrics?.length) {
      return [];
    }

    const desiredCount = Math.min(4, metrics.length);
    const normalized = metrics.map((metric) => ({
      metric,
      name: (metric.name || '').toUpperCase(),
      numericValue: typeof metric.value === 'number' && Number.isFinite(metric.value) ? metric.value : null,
      textValue: (metric.value_text ?? '').toString().trim(),
    }));

    const used = new Set<string>();
    const summary: SummaryMetric[] = [];

    const addMetric = (entry: (typeof normalized)[number]) => {
      if (!entry.metric.name || used.has(entry.metric.name)) {
        return;
      }
      const value = this.formatMetricValue(entry.metric);
      if (!value) {
        return;
      }
      summary.push({
        name: entry.metric.name,
        value,
        unit: entry.metric.unit ?? null,
      });
      used.add(entry.metric.name);
    };

    const findFirst = (predicate: (entry: (typeof normalized)[number]) => boolean) =>
      normalized.find((entry) => !used.has(entry.metric.name) && predicate(entry));

    const isEgfr = (name: string) => /TFG|EGFR|FILTRACION|GLOMERULAR/.test(name);
    const isCreatinine = (name: string) => /CREATININA|CREATININE/.test(name);

    const egfr = findFirst((entry) => entry.numericValue !== null && isEgfr(entry.name));
    if (egfr) addMetric(egfr);

    const creatinine = findFirst((entry) => entry.numericValue !== null && isCreatinine(entry.name));
    if (creatinine) addMetric(creatinine);

    normalized
      .filter((entry) => entry.numericValue !== null && !used.has(entry.metric.name))
      .some((entry) => {
        addMetric(entry);
        return summary.length >= Math.min(3, desiredCount);
      });

    if (summary.length < desiredCount) {
      normalized
        .filter((entry) => entry.numericValue === null && entry.textValue && !used.has(entry.metric.name))
        .some((entry) => {
          addMetric(entry);
          return summary.length >= desiredCount;
        });
    }

    return summary;
  }

  private formatMetricValue(metric: MetricBrief): string {
    if (typeof metric.value === 'number' && Number.isFinite(metric.value)) {
      const rounded = Math.abs(metric.value) < 100 ? metric.value.toFixed(2) : metric.value.toFixed(1);
      return rounded.replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
    }
    const textValue = (metric.value_text ?? '').toString().trim();
    return textValue;
  }

  private getSourceLabel(analysis: AnalysisSummary): string | null {
    const rawSource = analysis.source ?? analysis.source_pdf ?? '';
    if (!rawSource) {
      return null;
    }
    const normalized = rawSource.toLowerCase();
    if (normalized === 'unknown') {
      return null;
    }
    if (normalized.includes('ocr')) {
      return 'OCR';
    }
    if (normalized.includes('import')) {
      return 'Import';
    }
    if (normalized.includes('pdf')) {
      return 'PDF';
    }
    return rawSource;
  }
}

interface SummaryMetric {
  name: string;
  value: string;
  unit?: string | null;
}
