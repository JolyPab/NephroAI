import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { ApiService } from './api.service';
import { DoctorNote, DoctorPatientSummary } from '../models/doctor.model';
import { MetricSeriesResponse } from '../models/analysis.model';

@Injectable({ providedIn: 'root' })
export class DoctorService {
  private readonly api = inject(ApiService);

  listPatients(): Observable<{ patients: DoctorPatientSummary[] }> {
    return this.api
      .get<{ patients: DoctorPatientSummary[] }>('/doctor/patients')
      .pipe(
        catchError(() => of({ patients: [] }))
      );
  }

  getAnalyses(patientId: string): Observable<any[]> {
    return this.api.get<any[]>(`/doctor/patient/${patientId}/analyses`);
  }

  getSeries(patientId: string, metricName: string): Observable<MetricSeriesResponse> {
    return this.api.get<MetricSeriesResponse>(`/doctor/patient/${patientId}/series`, { name: metricName });
  }

  getNotes(patientId: string): Observable<DoctorNote[]> {
    return this.api.get<DoctorNote[]>(`/doctor/patient/${patientId}/notes`).pipe(catchError(() => of([])));
  }

  addNote(patientId: string, text: string, metricName?: string, metricTime?: string): Observable<DoctorNote> {
    return this.api.post<DoctorNote>(`/doctor/patient/${patientId}/notes`, {
      text,
      metric_name: metricName,
      metric_time: metricTime,
    });
  }
}
