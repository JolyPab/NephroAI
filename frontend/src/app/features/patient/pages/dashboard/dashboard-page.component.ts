import { Component, OnInit, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

import { PatientService } from '../../../../core/services/patient.service';
import { AnalysisSummary, MetricBrief } from '../../../../core/models/analysis.model';

@Component({
  selector: 'app-patient-dashboard-page',
  standalone: false,
  templateUrl: './dashboard-page.component.html',
  styleUrls: ['./dashboard-page.component.scss'],
})
export class PatientDashboardPageComponent implements OnInit {
  private readonly patientService = inject(PatientService);
  private readonly translate = inject(TranslateService);

  loading = true;
  analyses: AnalysisSummary[] = [];
  latestAnalysis: AnalysisSummary | null = null;
  summaryMetrics: SummaryMetric[] = [];
  errorMessage = '';

  ngOnInit(): void {
    this.patientService.getAnalyses().subscribe({
      next: (analyses) => {
        this.analyses = analyses ?? [];
        this.latestAnalysis = this.pickLatestAnalysis(this.analyses);
        this.summaryMetrics = this.latestAnalysis
          ? this.buildSummaryMetrics(this.latestAnalysis.metrics ?? [])
          : [];
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.DASHBOARD_LOAD_FAILED');
        this.loading = false;
      },
    });
  }

  latestDate(analysis: AnalysisSummary): string | null {
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
}

interface SummaryMetric {
  name: string;
  value: string;
  unit?: string | null;
}
