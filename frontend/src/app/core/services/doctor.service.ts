import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { ApiService } from './api.service';
import { ConsultationCall, ConsultationMessage, ConsultationThread } from '../models/consultation.model';
import { DoctorNote, DoctorPatientSummary } from '../models/doctor.model';
import { MetricSeriesResponse } from '../models/analysis.model';
import { DoctorChatContext, DoctorChatHistoryItem, DoctorChatResponse } from '../models/doctor-chat.model';

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

  getConsultations(): Observable<ConsultationThread[]> {
    return this.api.get<ConsultationThread[]>('/consultations').pipe(catchError(() => of([])));
  }

  createConsultationThread(patientId: number): Observable<ConsultationThread> {
    return this.api.post<ConsultationThread>('/consultations/threads', { patient_id: patientId });
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

  getActiveConsultationCalls(): Observable<ConsultationCall[]> {
    return this.api.get<ConsultationCall[]>('/consultations/calls/active').pipe(catchError(() => of([])));
  }

  startConsultationCall(threadId: number): Observable<ConsultationCall> {
    return this.api.post<ConsultationCall>('/consultations/calls', { thread_id: threadId });
  }

  updateConsultationCall(callId: number, action: 'accept' | 'decline' | 'end'): Observable<ConsultationCall> {
    return this.api.post<ConsultationCall>(`/consultations/calls/${callId}/action`, { action });
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

  getChatContext(patientId: string): Observable<DoctorChatContext> {
    return this.api.get<DoctorChatContext>(`/doctor/patient/${patientId}/chat/context`);
  }

  sendChatMessage(
    patientId: string,
    message: string,
    history?: DoctorChatHistoryItem[],
  ): Observable<DoctorChatResponse> {
    return this.api.post<DoctorChatResponse>(`/doctor/patient/${patientId}/chat`, {
      message,
      history,
    });
  }
}
