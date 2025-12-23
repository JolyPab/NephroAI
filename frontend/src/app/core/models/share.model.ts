export interface ShareRequest {
  doctor_email: string;
}

export interface ShareGrant {
  doctor_email: string;
  doctor_id?: number | null;
  doctor_name?: string | null;
  granted_at: string;
  revoked_at?: string | null;
}
