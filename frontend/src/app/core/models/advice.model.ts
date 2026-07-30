export interface AdviceMetric {
  name: string;
  value: number;
  unit?: string | null;
  dateISO: string;
}

export interface AdviceResponseModel {
  answer: string;
  usedMetrics: AdviceMetric[];
  disclaimer: boolean;
  session_id?: number | null;
  ai_messages_limit?: number;
  ai_messages_remaining?: number;
  ai_messages_reset_at?: string | null;
  scope_rejected?: boolean;
}
