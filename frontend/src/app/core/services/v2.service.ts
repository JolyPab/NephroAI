import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';
import {
  V2AnalyteItemResponse,
  V2DoctorNoteResponse,
  V2DoctorPatientResponse,
  V2SeriesResponse,
  V2UpsertDoctorNoteRequest,
  V2UploadResponse,
} from '../models/v2.model';

@Injectable({ providedIn: 'root' })
export class V2Service {
  private readonly api = inject(ApiService);

  uploadDocument(file: File): Observable<V2UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.api.postForm<V2UploadResponse>('/v2/documents', formData);
  }

  getAnalytes(): Observable<V2AnalyteItemResponse[]> {
    return this.api.get<V2AnalyteItemResponse[]>('/v2/analytes');
  }

  listAnalytes(): Observable<V2AnalyteItemResponse[]> {
    return this.getAnalytes();
  }

  getSeries(analyteKey: string): Observable<V2SeriesResponse> {
    return this.api.get<V2SeriesResponse>('/v2/series', { analyte_key: analyteKey });
  }

  listDoctorPatients(): Observable<V2DoctorPatientResponse[]> {
    return this.api.get<V2DoctorPatientResponse[]>('/v2/doctor/patients');
  }

  listPatientAnalytes(patientId: string | number): Observable<V2AnalyteItemResponse[]> {
    return this.api.get<V2AnalyteItemResponse[]>(`/v2/doctor/patients/${patientId}/analytes`);
  }

  getPatientSeries(patientId: string | number, analyteKey: string): Observable<V2SeriesResponse> {
    return this.api.get<V2SeriesResponse>(`/v2/doctor/patients/${patientId}/series`, { analyte_key: analyteKey });
  }

  listMyNotes(analyteKey: string): Observable<V2DoctorNoteResponse[]> {
    return this.api.get<V2DoctorNoteResponse[]>('/v2/notes', { analyte_key: analyteKey });
  }

  listDoctorNotes(patientId: string | number, analyteKey: string): Observable<V2DoctorNoteResponse[]> {
    return this.api.get<V2DoctorNoteResponse[]>(`/v2/doctor/patients/${patientId}/notes`, { analyte_key: analyteKey });
  }

  upsertDoctorNote(patientId: string | number, payload: V2UpsertDoctorNoteRequest): Observable<V2DoctorNoteResponse> {
    return this.api.post<V2DoctorNoteResponse>(`/v2/doctor/patients/${patientId}/notes`, payload);
  }

  getDoctorNotesUpsertUrl(patientId: string | number): string {
    return this.api.resolveUrl(`/v2/doctor/patients/${patientId}/notes`);
  }
}
