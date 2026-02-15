import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';

import { V2AnalyteItemResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../../v2/i18n/analyte-display';

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

  analytes: V2AnalyteItemResponse[] = [];
  selectedMetric = '';
  isLoading = true;
  errorMessage = '';
  language: V2DashboardLang = 'en';
  private pendingSelectedAnalyteKey: string | null = null;

  ngOnInit(): void {
    this.language = this.loadV2Language();
    this.route.queryParamMap.subscribe((params) => {
      const requested = params.get('analyte_key');
      if (!requested) {
        return;
      }
      if (this.analytes.some((item) => item.analyte_key === requested)) {
        this.selectedMetric = requested;
        return;
      }
      this.pendingSelectedAnalyteKey = requested;
    });
    this.loadAnalytes();
  }

  onMetricChange(metric: string): void {
    this.selectedMetric = metric;
    this.syncQueryMetric(metric);
  }

  getDisplayName(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
  }

  private loadAnalytes(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.v2Service.listAnalytes().subscribe({
      next: (rows) => {
        this.analytes = rows ?? [];
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
    return stored === 'es' || stored === 'en' ? stored : 'en';
  }

  private sortByDisplay(items: V2AnalyteItemResponse[]): V2AnalyteItemResponse[] {
    const copy = [...items];
    copy.sort((a, b) => {
      const labelA = this.getDisplayName(a);
      const labelB = this.getDisplayName(b);
      return labelA.localeCompare(labelB, this.language);
    });
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
}
