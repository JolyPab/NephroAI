import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';

import { ConsultationCall, ConsultationMessage, ConsultationThread } from '../../../../core/models/consultation.model';
import { ConsultationRealtimeEvent, ConsultationRealtimeService } from '../../../../core/services/consultation-realtime.service';
import { DoctorService } from '../../../../core/services/doctor.service';

@Component({
  selector: 'app-doctor-consultations-page',
  standalone: false,
  templateUrl: './doctor-consultations-page.component.html',
  styleUrls: ['./doctor-consultations-page.component.scss'],
})
export class DoctorConsultationsPageComponent implements OnInit, OnDestroy {
  private readonly doctorService = inject(DoctorService);
  private readonly route = inject(ActivatedRoute);
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
  openingPatientId: number | null = null;
  sending = false;
  draftMessage = '';
  errorMessage = '';
  activeCall: ConsultationCall | null = null;
  callBusy = false;
  private requestedPatientId: number | null = null;

  ngOnInit(): void {
    const rawPatientId = this.route.snapshot.queryParamMap.get('patient_id');
    this.requestedPatientId = rawPatientId ? Number(rawPatientId) : null;
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

    this.openingPatientId = consultation.patient_id;
    this.doctorService.createConsultationThread(consultation.patient_id).subscribe({
      next: (thread) => {
        this.openingPatientId = null;
        this.selectedConsultation = thread;
        this.consultations = this.consultations.map((item) =>
          item.patient_id === thread.patient_id ? thread : item,
        );
        if (thread.id) {
          this.loadMessages(thread.id);
          this.startMessagePolling(thread.id);
        }
      },
      error: (err) => {
        this.openingPatientId = null;
        this.errorMessage = err?.error?.detail ?? 'No se pudo abrir la consulta.';
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
    this.doctorService.sendConsultationMessage(threadId, body).subscribe({
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
        this.errorMessage = err?.error?.detail ?? 'No se pudo enviar el mensaje.';
      },
    });
  }

  startCall(): void {
    const threadId = this.selectedConsultation?.id;
    if (!threadId || !this.selectedConsultation?.can_call || this.callBusy) {
      return;
    }
    this.callBusy = true;
    this.doctorService.startConsultationCall(threadId).subscribe({
      next: (call) => {
        this.activeCall = call;
        this.callBusy = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'No se pudo iniciar la llamada.';
        this.callBusy = false;
      },
    });
  }

  endCall(): void {
    if (!this.activeCall || this.callBusy) {
      return;
    }
    this.callBusy = true;
    this.doctorService.updateConsultationCall(this.activeCall.id, 'end').subscribe({
      next: (call) => {
        this.activeCall = call.status === 'ringing' || call.status === 'accepted' ? call : null;
        this.callBusy = false;
      },
      error: () => {
        this.callBusy = false;
      },
    });
  }

  trackByPatient(_: number, item: ConsultationThread): number {
    return item.patient_id;
  }

  trackByMessage(_: number, item: ConsultationMessage): number {
    return item.id;
  }

  private loadMessages(threadId: number): void {
    this.loadingMessages = true;
    this.doctorService.getConsultationMessages(threadId).subscribe((messages) => {
      this.messages = messages ?? [];
      this.loadingMessages = false;
      this.markCurrentThreadRead(threadId);
      this.scrollMessagesToBottom();
    });
  }

  private refreshMessages(threadId: number): void {
    this.doctorService.getConsultationMessages(threadId).subscribe((messages) => {
      this.messages = messages ?? [];
      this.markCurrentThreadRead(threadId);
      this.scrollMessagesToBottom();
    });
  }

  private markCurrentThreadRead(threadId: number): void {
    this.doctorService.markConsultationRead(threadId).subscribe(() => {
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
    this.doctorService.getConsultations().subscribe((consultations) => {
      this.consultations = consultations ?? [];
      this.loading = false;

      if (this.selectedConsultation) {
        const updatedSelection = this.consultations.find(
          (item) => item.patient_id === this.selectedConsultation?.patient_id,
        );
        if (updatedSelection) {
          this.selectedConsultation = { ...updatedSelection, unread_count: this.selectedConsultation.unread_count };
        }
      }

      if (selectFirst && !this.selectedConsultation && this.consultations.length) {
        const requested = Number.isFinite(this.requestedPatientId)
          ? this.consultations.find((item) => item.patient_id === this.requestedPatientId)
          : null;
        this.selectedConsultation = requested ?? this.consultations[0];
        if (this.selectedConsultation.id) {
          this.loadMessages(this.selectedConsultation.id);
          this.startMessagePolling(this.selectedConsultation.id);
        } else if (requested) {
          this.openConsultation(requested);
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
    this.doctorService.getActiveConsultationCalls().subscribe((calls) => {
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
