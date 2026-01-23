import { Component, OnInit, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

import { PatientService } from '../../../../core/services/patient.service';
import { AnalysisSummary } from '../../../../core/models/analysis.model';

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
  errorMessage = '';

  ngOnInit(): void {
    this.patientService.getAnalyses().subscribe({
      next: (analyses) => {
        this.analyses = analyses ?? [];
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.DASHBOARD_LOAD_FAILED');
        this.loading = false;
      },
    });
  }

}
