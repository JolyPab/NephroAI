export interface V2CreateDocumentResponse {
  document_id: string;
  analysis_date: string | null;
  num_metrics: number;
}

export interface V2CreateDocumentDuplicateResponse {
  status: 'duplicate';
  document_id: string;
  analysis_date: string | null;
  num_metrics: number;
}

export interface V2DocumentListItemResponse {
  id: string;
  source_filename: string | null;
  analysis_date: string | null;
  report_date: string | null;
  created_at: string | null;
  num_metrics: number;
}

export interface V2DeleteDocumentResponse {
  status: 'deleted';
  document_id: string;
  num_metrics_deleted: number;
}

export type V2UploadResponse = V2CreateDocumentResponse | V2CreateDocumentDuplicateResponse;

export interface V2AnalyteItemResponse {
  analyte_key: string;
  raw_name?: string | null;
  last_value_numeric: number | null;
  last_value_text: string | null;
  last_date: string | null;
  unit: string | null;
}

export interface V2DoctorPatientResponse {
  patient_id: number;
  display_name: string | null;
  email: string | null;
  granted_at: string | null;
  latest_analysis_date: string | null;
}

export interface V2SeriesPointResponse {
  t: string | null;
  y: number | null;
  text: string | null;
  page: number | null;
  evidence: string | null;
}

export interface V2SeriesResponse {
  analyte_key: string;
  raw_name?: string | null;
  series_type: 'numeric' | 'text' | 'binary' | 'ordinal';
  unit: string | null;
  reference: Record<string, unknown> | null;
  points: V2SeriesPointResponse[];
}

export interface V2DoctorNoteResponse {
  id: string;
  analyte_key: string;
  t: string;
  note: string;
  doctor_id: number;
  doctor_name: string | null;
  updated_at: string;
}

export interface V2UpsertDoctorNoteRequest {
  analyte_key: string;
  t: string;
  note: string;
}
