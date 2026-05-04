import { Injectable, inject } from '@angular/core';
import { Observable, Subject } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ConsultationCall, ConsultationMessage, ConsultationThread } from '../models/consultation.model';
import { TokenService } from './token.service';

export interface ConsultationRealtimeEvent {
  type: 'thread.updated' | 'message.created' | 'messages.read' | 'call.updated';
  thread_id?: number;
  patient_id?: number;
  doctor_id?: number;
  thread?: ConsultationThread;
  message?: ConsultationMessage;
  call?: ConsultationCall;
  reader_user_id?: number;
  updated?: number;
}

@Injectable({ providedIn: 'root' })
export class ConsultationRealtimeService {
  private readonly tokens = inject(TokenService);
  private readonly eventsSubject = new Subject<ConsultationRealtimeEvent>();
  private socket?: WebSocket;
  private reconnectTimer?: ReturnType<typeof setTimeout>;
  private manuallyClosed = false;

  readonly events$: Observable<ConsultationRealtimeEvent> = this.eventsSubject.asObservable();

  connect(): void {
    const token = this.tokens.accessToken;
    if (!token || this.socket?.readyState === WebSocket.OPEN || this.socket?.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.manuallyClosed = false;
    const socket = new WebSocket(`${this.wsBaseUrl()}/consultations/ws?token=${encodeURIComponent(token)}`);
    this.socket = socket;

    socket.onmessage = (message) => {
      try {
        this.eventsSubject.next(JSON.parse(message.data) as ConsultationRealtimeEvent);
      } catch {
        // Ignore malformed realtime frames; polling remains as a fallback.
      }
    };

    socket.onclose = () => {
      if (this.socket === socket) {
        this.socket = undefined;
      }
      if (!this.manuallyClosed) {
        this.reconnectTimer = setTimeout(() => this.connect(), 2500);
      }
    };

    socket.onerror = () => socket.close();
  }

  disconnect(): void {
    this.manuallyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = undefined;
    }
    this.socket?.close();
    this.socket = undefined;
  }

  private wsBaseUrl(): string {
    const api = environment.BASE_API;
    const absolute = api.startsWith('http') ? api : `${window.location.origin}${api.startsWith('/') ? api : `/${api}`}`;
    return absolute.replace(/^http/, 'ws').replace(/\/$/, '');
  }
}
