import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { Subscription } from 'rxjs';

import { PatientService } from '../../../../core/services/patient.service';
import { ConsultationCall, ConsultationMessage, ConsultationThread } from '../../../../core/models/consultation.model';
import { ConsultationRealtimeEvent, ConsultationRealtimeService } from '../../../../core/services/consultation-realtime.service';

@Component({
  selector: 'app-patient-consultations-page',
  standalone: false,
  templateUrl: './consultations-page.component.html',
  styleUrls: ['./consultations-page.component.scss'],
})
export class PatientConsultationsPageComponent implements OnInit, OnDestroy {
  private readonly patientService = inject(PatientService);
  private readonly realtime = inject(ConsultationRealtimeService);
  private refreshTimer?: ReturnType<typeof setInterval>;
  private listRefreshTimer?: ReturnType<typeof setInterval>;
  private callRefreshTimer?: ReturnType<typeof setInterval>;
  private realtimeSubscription?: Subscription;

  @ViewChild('messageList') private messageList?: ElementRef<HTMLElement>;

  consultations: ConsultationThread[] = [];
  selectedConsultation: ConsultationThread | null = null;
  messages: ConsultationMessage[] = [];
  loading = true;
  loadingMessages = false;
  openingGrantId: number | null = null;
  sending = false;
  draftMessage = '';
  errorMessage = '';
  activeCall: ConsultationCall | null = null;
  callBusy = false;

  ngOnInit(): void {
    this.loadConsultations(true);
    this.startConsultationListPolling();
    this.refreshActiveCalls();
    this.startCallPolling();
    this.realtime.connect();
    this.realtimeSubscription = this.realtime.events$.subscribe((event) => this.handleRealtimeEvent(event));
  }

  ngOnDestroy(): void {
    this.realtimeSubscription?.unsubscribe();
    this.realtime.disconnect();
    this.stopMessagePolling();
    this.stopConsultationListPolling();
    this.stopCallPolling();
  }

  openConsultation(consultation: ConsultationThread): void {
    this.errorMessage = '';
    this.selectedConsultation = consultation;
    this.messages = [];

    if (consultation.id) {
      this.loadMessages(consultation.id);
      this.startMessagePolling(consultation.id);
      return;
    }

    this.openingGrantId = consultation.grant_id;
    this.patientService.createConsultationThread(consultation.grant_id).subscribe({
      next: (thread) => {
        this.openingGrantId = null;
        this.selectedConsultation = thread;
        this.consultations = this.consultations.map((item) =>
          item.grant_id === thread.grant_id ? thread : item,
        );
        if (thread.id) {
          this.loadMessages(thread.id);
          this.startMessagePolling(thread.id);
        }
      },
      error: (err) => {
        this.openingGrantId = null;
        this.errorMessage =
          err?.error?.detail ?? 'No se pudo abrir la consulta. Intenta de nuevo.';
      },
    });
  }

  sendMessage(): void {
    const body = this.draftMessage.trim();
    const threadId = this.selectedConsultation?.id;
    if (!body || !threadId || this.sending) {
      return;
    }

    this.sending = true;
    this.errorMessage = '';
    this.patientService.sendConsultationMessage(threadId, body).subscribe({
      next: (message) => {
        this.messages = [...this.messages, message];
        this.draftMessage = '';
        this.sending = false;
        this.consultations = this.consultations.map((item) =>
          item.id === threadId ? { ...item, last_message: message.body, updated_at: message.created_at } : item,
        );
        this.scrollMessagesToBottom();
      },
      error: (err) => {
        this.sending = false;
        this.errorMessage =
          err?.error?.detail ?? 'No se pudo enviar el mensaje. Intenta de nuevo.';
      },
    });
  }

  toggleCalls(): void {
    const consultation = this.selectedConsultation;
    if (!consultation) {
      return;
    }
    this.patientService
      .updateConsultationPermissions(consultation.grant_id, { can_call: !consultation.can_call })
      .subscribe((updated) => {
        this.selectedConsultation = updated;
        this.consultations = this.consultations.map((item) =>
          item.grant_id === updated.grant_id ? updated : item,
        );
      });
  }

  handleCall(action: 'accept' | 'decline' | 'end'): void {
    if (!this.activeCall || this.callBusy) {
      return;
    }
    this.callBusy = true;
    this.patientService.updateConsultationCall(this.activeCall.id, action).subscribe({
      next: (call) => {
        this.activeCall = call.status === 'ringing' || call.status === 'accepted' ? call : null;
        this.callBusy = false;
      },
      error: () => {
        this.callBusy = false;
      },
    });
  }

  trackByGrant(_: number, item: ConsultationThread): number {
    return item.grant_id;
  }

  trackByMessage(_: number, item: ConsultationMessage): number {
    return item.id;
  }

  private loadMessages(threadId: number): void {
    this.loadingMessages = true;
    this.patientService.getConsultationMessages(threadId).subscribe((messages) => {
      this.messages = messages ?? [];
      this.loadingMessages = false;
      this.markCurrentThreadRead(threadId);
      this.scrollMessagesToBottom();
    });
  }

  private refreshMessages(threadId: number): void {
    this.patientService.getConsultationMessages(threadId).subscribe((messages) => {
      this.messages = messages ?? [];
      this.markCurrentThreadRead(threadId);
      this.scrollMessagesToBottom();
    });
  }

  private markCurrentThreadRead(threadId: number): void {
    this.patientService.markConsultationRead(threadId).subscribe(() => {
      this.consultations = this.consultations.map((item) =>
        item.id === threadId ? { ...item, unread_count: 0 } : item,
      );
      if (this.selectedConsultation?.id === threadId) {
        this.selectedConsultation = { ...this.selectedConsultation, unread_count: 0 };
      }
    });
  }

  private startMessagePolling(threadId: number): void {
    this.stopMessagePolling();
    this.refreshTimer = setInterval(() => {
      if (this.selectedConsultation?.id === threadId && !this.sending) {
        this.refreshMessages(threadId);
      }
    }, 5000);
  }

  private stopMessagePolling(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = undefined;
    }
  }

  private loadConsultations(selectFirst: boolean): void {
    this.patientService.getConsultations().subscribe((consultations) => {
      this.consultations = consultations ?? [];
      this.loading = false;

      if (this.selectedConsultation) {
        const updatedSelection = this.consultations.find(
          (item) => item.grant_id === this.selectedConsultation?.grant_id,
        );
        if (updatedSelection) {
          this.selectedConsultation = { ...updatedSelection, unread_count: this.selectedConsultation.unread_count };
        }
      }

      if (selectFirst && !this.selectedConsultation && this.consultations.length) {
        this.selectedConsultation = this.consultations[0];
        if (this.selectedConsultation.id) {
          this.loadMessages(this.selectedConsultation.id);
          this.startMessagePolling(this.selectedConsultation.id);
        }
      }
    });
  }

  private startConsultationListPolling(): void {
    this.stopConsultationListPolling();
    this.listRefreshTimer = setInterval(() => this.loadConsultations(false), 7000);
  }

  private stopConsultationListPolling(): void {
    if (this.listRefreshTimer) {
      clearInterval(this.listRefreshTimer);
      this.listRefreshTimer = undefined;
    }
  }

  private refreshActiveCalls(): void {
    this.patientService.getActiveConsultationCalls().subscribe((calls) => {
      this.activeCall = (calls ?? [])[0] ?? null;
    });
  }

  private handleRealtimeEvent(event: ConsultationRealtimeEvent): void {
    if (event.type === 'call.updated') {
      this.activeCall = event.call && ['ringing', 'accepted'].includes(event.call.status) ? event.call : null;
      return;
    }

    this.loadConsultations(false);
    const threadId = this.selectedConsultation?.id;
    if (threadId && event.thread_id === threadId && event.type !== 'messages.read') {
      this.refreshMessages(threadId);
    }
  }

  private startCallPolling(): void {
    this.stopCallPolling();
    this.callRefreshTimer = setInterval(() => this.refreshActiveCalls(), 3000);
  }

  private stopCallPolling(): void {
    if (this.callRefreshTimer) {
      clearInterval(this.callRefreshTimer);
      this.callRefreshTimer = undefined;
    }
  }

  private scrollMessagesToBottom(): void {
    setTimeout(() => {
      const element = this.messageList?.nativeElement;
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    });
  }
}
