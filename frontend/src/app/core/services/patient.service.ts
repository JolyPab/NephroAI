import { Injectable, inject } from '@angular/core';
import { catchError } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

import { ApiService } from './api.service';
import { AnalysisSummary, MetricSeriesResponse } from '../models/analysis.model';
import { ConsultationCall, ConsultationMessage, ConsultationThread } from '../models/consultation.model';
import { ShareGrant } from '../models/share.model';
import { DoctorNote } from '../models/doctor.model';

@Injectable({ providedIn: 'root' })
export class PatientService {
  private readonly api = inject(ApiService);

  getAnalyses(): Observable<AnalysisSummary[]> {
    return this.api.get<AnalysisSummary[]>('/patient/analyses');
  }

  getSeries(metricName: string): Observable<MetricSeriesResponse> {
    return this.api.get<MetricSeriesResponse>('/patient/series', { name: metricName });
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

  getConsultations(): Observable<ConsultationThread[]> {
    return this.api.get<ConsultationThread[]>('/consultations').pipe(catchError(() => of([])));
  }

  createConsultationThread(grantId: number): Observable<ConsultationThread> {
    return this.api.post<ConsultationThread>('/consultations/threads', { grant_id: grantId });
  }

  getConsultationMessages(threadId: number): Observable<ConsultationMessage[]> {
    return this.api
      .get<ConsultationMessage[]>(`/consultations/threads/${threadId}/messages`)
      .pipe(catchError(() => of([])));
  }

  sendConsultationMessage(threadId: number, body: string): Observable<ConsultationMessage> {
    return this.api.post<ConsultationMessage>(`/consultations/threads/${threadId}/messages`, { body });
  }

  markConsultationRead(threadId: number): Observable<{ updated: number }> {
    return this.api.post<{ updated: number }>(`/consultations/threads/${threadId}/read`, {});
  }

  updateConsultationPermissions(
    grantId: number,
    permissions: { can_message?: boolean; can_call?: boolean },
  ): Observable<ConsultationThread> {
    return this.api.patch<ConsultationThread>(`/consultations/grants/${grantId}/permissions`, permissions);
  }

  getActiveConsultationCalls(): Observable<ConsultationCall[]> {
    return this.api.get<ConsultationCall[]>('/consultations/calls/active').pipe(catchError(() => of([])));
  }

  updateConsultationCall(callId: number, action: 'accept' | 'decline' | 'end'): Observable<ConsultationCall> {
    return this.api.post<ConsultationCall>(`/consultations/calls/${callId}/action`, { action });
  }

  getDoctorNotes(metricName?: string): Observable<DoctorNote[]> {
    return this.api
      .get<DoctorNote[]>('/patient/notes', { name: metricName ?? '' })
      .pipe(catchError(() => of([])));
  }
}
