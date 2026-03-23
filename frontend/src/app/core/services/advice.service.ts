import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';
import { AdviceResponseModel } from '../models/advice.model';
import { ChatSessionSummary, ChatSessionMessage, PatientMemoryFact } from '../models/chat-session.model';

@Injectable({ providedIn: 'root' })
export class AdviceClientService {
  private readonly api = inject(ApiService);

  ask(
    question: string,
    metricNames?: string[],
    days?: number,
    language?: 'es' | 'en',
    sessionId?: number,
  ): Observable<AdviceResponseModel> {
    return this.api.post<AdviceResponseModel>('/advice', {
      question,
      metricNames,
      days,
      language,
      session_id: sessionId,
    });
  }

  getSessions(): Observable<ChatSessionSummary[]> {
    return this.api.get<ChatSessionSummary[]>('/chat/sessions');
  }

  createSession(): Observable<ChatSessionSummary> {
    return this.api.post<ChatSessionSummary>('/chat/sessions', {});
  }

  getMessages(sessionId: number): Observable<ChatSessionMessage[]> {
    return this.api.get<ChatSessionMessage[]>(`/chat/sessions/${sessionId}/messages`);
  }

  deleteSession(sessionId: number): Observable<unknown> {
    return this.api.delete<unknown>(`/chat/sessions/${sessionId}`);
  }

  getMemory(): Observable<PatientMemoryFact[]> {
    return this.api.get<PatientMemoryFact[]>('/chat/memory');
  }

  deleteMemory(factId: number): Observable<unknown> {
    return this.api.delete<unknown>(`/chat/memory/${factId}`);
  }
}
