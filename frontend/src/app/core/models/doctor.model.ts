export interface DoctorPatientSummary {
  patient_id: string;
  email?: string | null;
  full_name?: string | null;
  granted_at: string;
  latest_taken_at?: string | null;
}

export interface DoctorNote {
  id: number;
  text: string;
  doctor_id: number;
  doctor_email?: string | null;
  metric_name?: string | null;
  metric_time?: string | null;
  created_at: string;
}
