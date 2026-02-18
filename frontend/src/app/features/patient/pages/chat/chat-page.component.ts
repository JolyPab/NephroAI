import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';

import { AdviceClientService } from '../../../../core/services/advice.service';
import { AdviceResponseModel } from '../../../../core/models/advice.model';
import { ChatMessage } from '../../../../core/models/chat.model';
import { V2AnalyteItemResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../../v2/i18n/analyte-display';

@Component({
  selector: 'app-patient-chat-page',
  standalone: false,
  templateUrl: './chat-page.component.html',
  styleUrls: ['./chat-page.component.scss'],
})
export class PatientChatPageComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly adviceService = inject(AdviceClientService);
  private readonly v2Service = inject(V2Service);

  isLoading = false;
  availableMetrics: string[] = [];
  history: ChatMessage[] = [];
  errorMessage = '';
  patientSnapshot = '';
  language: V2DashboardLang = 'es';
  quickPrompts: string[] = [
    'Summarize my recent lab trends.',
    'Which metrics are out of range?',
    'What should I discuss with my doctor?'
  ];
  private readonly promptCopy: Record<
    V2DashboardLang,
    { base: string[]; metricTemplate: string }
  > = {
    en: {
      base: [
        'Summarize my recent lab trends.',
        'Which metrics are out of range?',
        'What should I discuss with my doctor?',
      ],
      metricTemplate: 'How did {{metric}} change recently?',
    },
    es: {
      base: [
        'Resume mis tendencias recientes de laboratorio.',
        'Que metricas estan fuera de rango?',
        'Que deberia hablar con mi medico?',
      ],
      metricTemplate: 'Como cambio {{metric}} recientemente?',
    },
  };

  readonly chatForm = this.fb.nonNullable.group({
    question: ['', [Validators.required, Validators.minLength(10)]],
    metricNames: [[] as string[]],
    days: [180],
  });

  ngOnInit(): void {
    this.language = this.loadV2Language();
    this.v2Service.listAnalytes().subscribe((analytes) => {
      const sorted = this.sortByRecent(analytes ?? []);
      this.availableMetrics = sorted.map((item) => this.getDisplayName(item)).slice(0, 40);
      this.patientSnapshot = this.buildPatientSnapshot(sorted.slice(0, 40));
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

    const requestQuestion = this.withPatientSnapshot(question);
    const pendingIndex = this.appendPendingMessage(question);

    this.adviceService
      .ask(
        requestQuestion,
        metricNames && metricNames.length ? metricNames : undefined,
        days,
        this.language,
      )
      .subscribe({
        next: (response) => this.handleResponse(question, response, pendingIndex),
        error: (err) => {
          this.removePendingMessage(pendingIndex);
          this.errorMessage = err?.error?.detail ?? 'Failed to get advice. Please try again.';
          this.isLoading = false;
        },
      });
  }

  private handleResponse(question: string, response: AdviceResponseModel, pendingIndex: number): void {
    const safeAnswer = this.normalizeAdviceAnswer(response.answer);
    const updatedMessage: ChatMessage = {
      question,
      answer: safeAnswer,
      metrics: response.usedMetrics,
      disclaimer: response.disclaimer,
      timestamp: this.history[pendingIndex]?.timestamp ?? new Date(),
    };
    this.upsertPendingMessage(pendingIndex, updatedMessage);

    this.isLoading = false;
    this.chatForm.patchValue({ question: '' });
  }

  private appendPendingMessage(question: string): number {
    this.history = [
      ...this.history,
      {
        question,
        answer: '',
        metrics: [],
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

  private buildPrompts(): void {
    const copy = this.promptCopy[this.language] ?? this.promptCopy.en;
    const metricPrompts = this.availableMetrics
      .slice(0, 3)
      .map((metric) => copy.metricTemplate.replace('{{metric}}', metric));
    const base = copy.base;
    this.quickPrompts = [...base, ...metricPrompts].slice(0, 6);
  }

  private withPatientSnapshot(question: string): string {
    if (!this.patientSnapshot) {
      return question;
    }
    return `${question}\n\nPatient labs snapshot:\n${this.patientSnapshot}`;
  }

  private buildPatientSnapshot(analytes: V2AnalyteItemResponse[]): string {
    return analytes
      .map((item) => {
        const label = this.getDisplayName(item);
        const value = this.formatValue(item);
        const date = this.formatDate(item.last_date);
        const ref = this.formatReferenceLabel(item);
        return `${label} (${item.analyte_key}): ${value} — ${date} (Ref: ${ref})`;
      })
      .join('\n');
  }

  private getDisplayName(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
  }

  private formatValue(item: V2AnalyteItemResponse): string {
    if (item.last_value_numeric !== null && item.last_value_numeric !== undefined) {
      const numeric = Number.isInteger(item.last_value_numeric)
        ? String(item.last_value_numeric)
        : item.last_value_numeric.toFixed(2).replace(/\.?0+$/, '');
      return `${numeric}${item.unit ? ` ${item.unit}` : ''}`;
    }
    const text = item.last_value_text?.trim();
    return text || '-';
  }

  private formatDate(dateRaw: string | null): string {
    if (!dateRaw) {
      return '-';
    }
    const ts = Date.parse(dateRaw);
    if (!Number.isFinite(ts)) {
      return dateRaw;
    }
    return new Date(ts).toLocaleDateString(this.language === 'es' ? 'es-ES' : 'en-US');
  }

  private sortByRecent(items: V2AnalyteItemResponse[]): V2AnalyteItemResponse[] {
    return [...items].sort((a, b) => this.dateTimestamp(b.last_date) - this.dateTimestamp(a.last_date));
  }

  private dateTimestamp(value: string | null): number {
    if (!value) {
      return 0;
    }
    const ts = Date.parse(value);
    return Number.isFinite(ts) ? ts : 0;
  }

  private loadV2Language(): V2DashboardLang {
    const stored = localStorage.getItem('v2_lang');
    if (stored === 'es' || stored === 'en') {
      return stored;
    }
    const current = (document.documentElement.lang || '').toLowerCase();
    if (current.startsWith('es')) {
      return 'es';
    }
    if (current.startsWith('en')) {
      return 'en';
    }
    return 'es';
  }

  private formatReferenceLabel(item: V2AnalyteItemResponse): string {
    const withRef = item as V2AnalyteItemResponse & {
      reference?: Record<string, unknown> | null;
      reference_json?: Record<string, unknown> | null;
    };
    const reference = withRef.reference ?? withRef.reference_json ?? null;
    if (!reference) {
      return '-';
    }

    const type = typeof reference['type'] === 'string' ? String(reference['type']).toLowerCase() : '';
    const min = this.toNumber(reference['min']);
    const max = this.toNumber(reference['max']);
    const threshold = this.toNumber(reference['threshold']);

    if (type === 'categorical' && Array.isArray(reference['categories'])) {
      const summary = (reference['categories'] as unknown[])
        .map((entry) => this.formatCategory(entry))
        .filter((line): line is string => !!line)
        .slice(0, 4);
      return summary.length ? summary.join('; ') : '-';
    }

    if (min !== null && max !== null) {
      return `${this.formatNumeric(min)}-${this.formatNumeric(max)}`;
    }
    if ((type === 'max' || max !== null) && (threshold !== null || max !== null)) {
      return `< ${this.formatNumeric(threshold ?? max ?? 0)}`;
    }
    if ((type === 'min' || min !== null) && (threshold !== null || min !== null)) {
      return `> ${this.formatNumeric(threshold ?? min ?? 0)}`;
    }
    return '-';
  }

  private formatCategory(entry: unknown): string | null {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      return null;
    }
    const category = entry as Record<string, unknown>;
    const label = typeof category['label'] === 'string' ? category['label'].trim() : '';
    if (!label) {
      return null;
    }
    const min = this.toNumber(category['min']);
    const max = this.toNumber(category['max']);
    if (min !== null && max !== null) {
      return `${label} ${this.formatNumeric(min)}-${this.formatNumeric(max)}`;
    }
    if (max !== null) {
      return `${label} <${this.formatNumeric(max)}`;
    }
    if (min !== null) {
      return `${label} >${this.formatNumeric(min)}`;
    }
    return label;
  }

  private toNumber(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value.trim().replace(',', '.'));
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  private formatNumeric(value: number): string {
    if (Number.isInteger(value)) {
      return String(value);
    }
    return value.toFixed(2).replace(/\.?0+$/, '');
  }

  private normalizeAdviceAnswer(answer: string | null | undefined): string {
    const text = (answer ?? '').trim();
    if (text) {
      return text;
    }
    return this.language === 'es'
      ? 'No pude generar un resumen util con los datos actuales. Intenta con una pregunta mas especifica sobre una metrica concreta.'
      : 'I could not build a useful summary from the current data. Try a more specific question about one metric.';
  }
}
