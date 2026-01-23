export interface ChatMetric {
  name: string;
  value: number;
  unit?: string | null;
}

export interface ChatMessage {
  question: string;
  answer: string;
  metrics?: ChatMetric[];
  disclaimer?: boolean;
  timestamp: Date;
}
