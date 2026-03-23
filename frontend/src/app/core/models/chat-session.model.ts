export interface ChatSessionSummary {
  id: number;
  title: string | null;
  updated_at: string | null;
  preview: string | null;
}

export interface ChatSessionMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface PatientMemoryFact {
  id: number;
  fact: string;
  category: 'medical' | 'preference' | 'recommendation';
  created_at: string;
}
