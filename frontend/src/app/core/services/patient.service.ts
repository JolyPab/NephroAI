import { Injectable, inject } from '@angular/core';
import { catchError } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

import { ApiService } from './api.service';
import { AnalysisSummary, MetricSeriesPoint } from '../models/analysis.model';
import { ShareGrant } from '../models/share.model';
import { DoctorNote } from '../models/doctor.model';

@Injectable({ providedIn: 'root' })
export class PatientService {
  private readonly api = inject(ApiService);

  getAnalyses(): Observable<AnalysisSummary[]> {
    return this.api.get<AnalysisSummary[]>('/patient/analyses');
  }

  getSeries(metricName: string): Observable<MetricSeriesPoint[]> {
    return this.api.get<MetricSeriesPoint[]>('/patient/series', { name: metricName });
  }

  uploadPdf(file: File): Observable<{ analysis_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.api.postForm<{ analysis_id: string }>('/files/pdf', formData);
  }

  shareWithDoctor(doctorEmail: string): Observable<ShareGrant> {
    return this.api.post<ShareGrant>('/share/grant', { doctor_email: doctorEmail });
  }

  getAccessGrants(): Observable<ShareGrant[]> {
    return this.api.get<ShareGrant[]>('/share/grants').pipe(catchError(() => of([])));
  }

  getDoctorNotes(metricName?: string): Observable<DoctorNote[]> {
    return this.api
      .get<DoctorNote[]>('/patient/notes', { name: metricName ?? '' })
      .pipe(catchError(() => of([])));
  }
}
