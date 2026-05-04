export interface ConsultationThread {
  id?: number | null;
  patient_id: number;
  patient_name?: string | null;
  doctor_id?: number | null;
  doctor_email: string;
  doctor_name?: string | null;
  grant_id: number;
  status: string;
  can_message: boolean;
  can_call: boolean;
  unread_count: number;
  last_message?: string | null;
  updated_at?: string | null;
}

export interface ConsultationMessage {
  id: number;
  thread_id: number;
  sender_user_id: number;
  sender_name?: string | null;
  sender_role: 'patient' | 'doctor';
  body: string;
  message_type: string;
  read_at?: string | null;
  created_at: string;
}

export interface ConsultationCall {
  id: number;
  thread_id: number;
  doctor_id: number;
  patient_id: number;
  patient_name?: string | null;
  doctor_name?: string | null;
  status: 'ringing' | 'accepted' | 'declined' | 'missed' | 'ended';
  livekit_room?: string | null;
  created_at: string;
  accepted_at?: string | null;
  ended_at?: string | null;
}
