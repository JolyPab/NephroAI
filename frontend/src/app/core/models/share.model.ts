export interface ShareRequest {
  doctor_email: string;
}

export interface ShareGrant {
  doctor_email: string;
  doctor_id?: number | null;
  doctor_name?: string | null;
  can_message?: boolean;
  can_call?: boolean;
  granted_at: string;
  revoked_at?: string | null;
}
