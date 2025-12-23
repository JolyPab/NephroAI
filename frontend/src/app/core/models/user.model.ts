export type UserRole = 'PATIENT' | 'DOCTOR' | 'ADMIN';

export interface User {
  id: number | string;  // Backend returns number
  email: string;
  role: UserRole;
  full_name?: string | null;
  is_doctor?: boolean;
  is_active?: boolean;
  created_at?: string;
}
