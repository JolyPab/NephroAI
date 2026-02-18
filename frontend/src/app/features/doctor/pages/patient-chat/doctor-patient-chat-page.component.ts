import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';

import { DoctorService } from '../../../../core/services/doctor.service';
import { ChatMessage } from '../../../../core/models/chat.model';
import { DoctorChatContext, DoctorChatHistoryItem, DoctorChatResponse } from '../../../../core/models/doctor-chat.model';
import { V2DashboardLang } from '../../../v2/i18n/analyte-display';

@Component({
  selector: 'app-doctor-patient-chat-page',
  standalone: false,
  templateUrl: './doctor-patient-chat-page.component.html',
  styleUrls: ['./doctor-patient-chat-page.component.scss'],
})
export class DoctorPatientChatPageComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly doctorService = inject(DoctorService);
  private readonly translate = inject(TranslateService);

  patientId = '';
  patientName = '';
  isLoading = false;
  contextLoading = true;
  hasLabData = true;
  history: ChatMessage[] = [];
  errorMessage = '';
  quickPrompts: string[] = [];

  private language: V2DashboardLang = 'es';
  private readonly promptCopy: Record<V2DashboardLang, string[]> = {
    en: [
      'Summarize kidney function trends.',
      'Explain abnormal values.',
      'What follow-up questions should I ask?',
      'Possible causes of lower eGFR?',
    ],
    es: [
      'Resume las tendencias de funcion renal.',
      'Explica los valores anormales.',
      'Que preguntas de seguimiento deberia hacer?',
      'Posibles causas de un eGFR mas bajo?',
    ],
  };

  readonly chatForm = this.fb.nonNullable.group({
    question: ['', [Validators.required, Validators.minLength(10)]],
  });

  private sub?: Subscription;

  ngOnInit(): void {
    this.language = this.loadUiLanguage();
    this.quickPrompts = [...(this.promptCopy[this.language] ?? this.promptCopy.en)];
    this.sub = this.route.paramMap.subscribe((params) => {
      this.patientId = params.get('id') ?? '';
      if (!this.patientId) {
        return;
      }
      this.loadPatientIdentity();
      this.loadContext();
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  get subtitleParams(): { patient: string } {
    const label = this.patientName || `#${this.patientId}`;
    return { patient: label };
  }

  setPrompt(prompt: string): void {
    this.chatForm.patchValue({ question: prompt });
  }

  submit(): void {
    if (this.chatForm.invalid || !this.patientId) {
      this.chatForm.markAllAsTouched();
      return;
    }
    if (!this.hasLabData) {
      return;
    }

    const { question } = this.chatForm.getRawValue();
    this.isLoading = true;
    this.errorMessage = '';
    const pendingIndex = this.appendPendingMessage(question);

    const historyPayload: DoctorChatHistoryItem[] = this.history
      .filter((item) => item.answer.trim().length > 0)
      .flatMap((item) => [
        { role: 'user' as const, content: item.question },
        { role: 'assistant' as const, content: item.answer },
      ])
      .slice(-8);

    this.doctorService.sendChatMessage(this.patientId, question, historyPayload).subscribe({
      next: (response: DoctorChatResponse) => {
        this.upsertPendingMessage(pendingIndex, {
          question,
          answer: this.normalizeReply(response.reply),
          disclaimer: response.disclaimer ?? false,
          timestamp: this.history[pendingIndex]?.timestamp ?? new Date(),
        });
        this.isLoading = false;
        this.chatForm.patchValue({ question: '' });
      },
      error: (err) => {
        this.removePendingMessage(pendingIndex);
        this.errorMessage = err?.error?.detail ?? 'Failed to get assistant response.';
        this.isLoading = false;
      },
    });
  }

  private loadContext(): void {
    this.contextLoading = true;
    this.doctorService.getChatContext(this.patientId).subscribe({
      next: (context: DoctorChatContext) => {
        const hasAnalyses = (context?.recent_analyses ?? []).length > 0;
        const hasMetrics = (context?.metrics_snapshot ?? []).length > 0;
        this.hasLabData = hasAnalyses || hasMetrics;
        this.contextLoading = false;
      },
      error: () => {
        this.hasLabData = false;
        this.contextLoading = false;
      },
    });
  }

  private loadPatientIdentity(): void {
    this.doctorService.listPatients().subscribe({
      next: (response) => {
        const match = response?.patients?.find((p) => `${p.patient_id}` === `${this.patientId}`);
        if (match) {
          this.patientName = match.full_name || match.email || '';
        }
      },
    });
  }

  private loadUiLanguage(): V2DashboardLang {
    const stored = localStorage.getItem('v2_lang');
    if (stored === 'es' || stored === 'en') {
      return stored;
    }
    const current = (this.translate.currentLang || '').toLowerCase();
    if (current.startsWith('es')) {
      return 'es';
    }
    if (current.startsWith('en')) {
      return 'en';
    }
    return 'es';
  }

  private appendPendingMessage(question: string): number {
    this.history = [
      ...this.history,
      {
        question,
        answer: '',
        disclaimer: false,
        timestamp: new Date(),
      },
    ];
    return this.history.length - 1;
  }

  private upsertPendingMessage(index: number, message: ChatMessage): void {
    if (index < 0 || index >= this.history.length) {
      this.history = [...this.history, message];
      return;
    }
    const nextHistory = [...this.history];
    nextHistory[index] = message;
    this.history = nextHistory;
  }

  private removePendingMessage(index: number): void {
    if (index < 0 || index >= this.history.length) {
      return;
    }
    this.history = this.history.filter((_, i) => i !== index);
  }

  private normalizeReply(reply: string | null | undefined): string {
    const text = (reply ?? '').trim();
    if (text) {
      return text;
    }
    return this.language === 'es'
      ? 'No pude generar una respuesta util con el contexto actual. Intenta una pregunta mas concreta.'
      : 'I could not generate a useful response with the current context. Try a more specific question.';
  }
}
