import { Component, OnInit, inject } from '@angular/core';

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
        this.errorMessage = err?.error?.detail ?? 'Failed to load analyses.';
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
}
