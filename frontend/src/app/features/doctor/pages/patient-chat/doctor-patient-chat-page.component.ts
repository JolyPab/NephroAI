import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';

import { DoctorService } from '../../../../core/services/doctor.service';
import { ChatMessage } from '../../../../core/models/chat.model';
import { DoctorChatContext, DoctorChatHistoryItem, DoctorChatResponse } from '../../../../core/models/doctor-chat.model';

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

  patientId = '';
  patientName = '';
  isLoading = false;
  contextLoading = true;
  hasLabData = true;
  history: ChatMessage[] = [];
  errorMessage = '';
  quickPrompts: string[] = [
    'Summarize kidney function trends.',
    'Explain abnormal values.',
    'What follow-up questions to ask?',
    'Possible causes of ↓eGFR?',
  ];

  readonly chatForm = this.fb.nonNullable.group({
    question: ['', [Validators.required, Validators.minLength(10)]],
  });

  private sub?: Subscription;

  ngOnInit(): void {
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

    const historyPayload: DoctorChatHistoryItem[] = this.history
      .flatMap((item) => [
        { role: 'user' as const, content: item.question },
        { role: 'assistant' as const, content: item.answer },
      ])
      .slice(-8);

    this.doctorService.sendChatMessage(this.patientId, question, historyPayload).subscribe({
      next: (response: DoctorChatResponse) => {
        this.history = [
          ...this.history,
          {
            question,
            answer: response.reply,
            disclaimer: response.disclaimer ?? false,
            timestamp: new Date(),
          },
        ];
        this.isLoading = false;
        this.chatForm.patchValue({ question: '' });
      },
      error: (err) => {
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
}
