import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';

import { AdviceClientService } from '../../../../core/services/advice.service';
import { AdviceResponseModel } from '../../../../core/models/advice.model';
import { PatientService } from '../../../../core/services/patient.service';

interface ChatMessage {
  question: string;
  answer: string;
  metrics: { name: string; value: number; unit?: string | null }[];
  disclaimer?: boolean;
  timestamp: Date;
}

@Component({
  selector: 'app-patient-chat-page',
  standalone: false,
  templateUrl: './chat-page.component.html',
  styleUrls: ['./chat-page.component.scss'],
})
export class PatientChatPageComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly adviceService = inject(AdviceClientService);
  private readonly patientService = inject(PatientService);

  isLoading = false;
  availableMetrics: string[] = [];
  history: ChatMessage[] = [];
  errorMessage = '';
  quickPrompts: string[] = [
    'Summarize my recent lab trends.',
    'Which metrics are out of range?',
    'What should I discuss with my doctor?'
  ];

  readonly chatForm = this.fb.nonNullable.group({
    question: ['', [Validators.required, Validators.minLength(10)]],
    metricNames: [[] as string[]],
    days: [180],
  });

  ngOnInit(): void {
    this.patientService.getAnalyses().subscribe((analyses) => {
      this.availableMetrics = Array.from(
        new Set(
          analyses
            ?.flatMap((analysis) => analysis.metrics?.map((metric) => metric.name) ?? [])
            .filter(Boolean)
        ),
      );
      this.buildPrompts();
    });
  }

  setPrompt(prompt: string): void {
    this.chatForm.patchValue({ question: prompt });
  }

  submit(): void {
    if (this.chatForm.invalid) {
      this.chatForm.markAllAsTouched();
      return;
    }

    const { question, metricNames, days } = this.chatForm.getRawValue();
    this.isLoading = true;
    this.errorMessage = '';

    this.adviceService
      .ask(question, metricNames && metricNames.length ? metricNames : undefined, days)
      .subscribe({
        next: (response) => this.handleResponse(question, response),
        error: (err) => {
          this.errorMessage = err?.error?.detail ?? 'Failed to get advice. Please try again.';
          this.isLoading = false;
        },
      });
  }

  private handleResponse(question: string, response: AdviceResponseModel): void {
    this.history = [
      ...this.history,
      {
        question,
        answer: response.answer,
        metrics: response.usedMetrics,
        disclaimer: response.disclaimer,
        timestamp: new Date(),
      },
    ];

    this.isLoading = false;
    this.chatForm.patchValue({ question: '' });
  }

  private buildPrompts(): void {
    const metricPrompts = this.availableMetrics.slice(0, 3).map((m) => `How did ${m} change recently?`);
    const base = [
      'Summarize my recent lab trends.',
      'Which metrics are out of range?',
      'What should I discuss with my doctor?',
    ];
    this.quickPrompts = [...base, ...metricPrompts].slice(0, 6);
  }
}
