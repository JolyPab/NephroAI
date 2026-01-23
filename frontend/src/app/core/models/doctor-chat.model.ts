export interface DoctorChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
}

export interface DoctorChatMetricSnapshot {
  name: string;
  value_num?: number | null;
  value_text?: string | null;
  unit?: string | null;
  ref_min?: number | null;
  ref_max?: number | null;
  date?: string | null;
}

export interface DoctorChatContext {
  patient: { id: number | string; name?: string | null };
  latest_analysis_date?: string | null;
  recent_analyses?: { date?: string | null; source?: string | null }[];
  metrics_snapshot?: DoctorChatMetricSnapshot[];
  trends?: Record<string, unknown>;
  egfr?: { latest_value?: number | null; stage?: string | null; stage_label?: string | null };
}

export interface DoctorChatResponse {
  reply: string;
  disclaimer?: boolean;
}
