import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { finalize } from 'rxjs/operators';

import { AdviceClientService } from '../../../../core/services/advice.service';
import { AdviceResponseModel } from '../../../../core/models/advice.model';
import { ChatMessage } from '../../../../core/models/chat.model';
import { ChatSessionSummary, ChatSessionMessage, PatientMemoryFact } from '../../../../core/models/chat-session.model';
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

  // ── Chat state ─────────────────────────────────────────────────────────
  isLoading = false;
  animateLastMessage = false;
  availableMetrics: string[] = [];
  history: ChatMessage[] = [];
  errorMessage = '';
  language: V2DashboardLang = 'es';

  // ── Session state ──────────────────────────────────────────────────────
  sessions: ChatSessionSummary[] = [];
  activeSessionId: number | null = null;
  sidebarOpen = false;

  // ── Memory state ───────────────────────────────────────────────────────
  memoryFacts: PatientMemoryFact[] = [];
  memoryPanelOpen = false;

  // ── Quick prompts ──────────────────────────────────────────────────────
  quickPrompts: string[] = [];
  private readonly promptCopy: Record<V2DashboardLang, { base: string[]; metricTemplate: string }> = {
    en: {
      base: ['Summarize my recent lab trends.', 'Which metrics are out of range?', 'What should I discuss with my doctor?'],
      metricTemplate: 'How did {{metric}} change recently?',
    },
    es: {
      base: ['Resume mis tendencias recientes de laboratorio.', 'Que metricas estan fuera de rango?', 'Que deberia hablar con mi medico?'],
      metricTemplate: 'Como cambio {{metric}} recientemente?',
    },
  };

  readonly chatForm = this.fb.nonNullable.group({
    question: ['', [Validators.required, Validators.minLength(10)]],
    metricNames: [[] as string[]],
    days: [180],
  });

  ngOnInit(): void {
    this.language = 'es';
    this.loadSessions();
    this.v2Service.listAnalytes().subscribe((analytes) => {
      const sorted = this.sortByRecent(analytes ?? []);
      this.availableMetrics = sorted.map(item => this.getDisplayName(item)).slice(0, 40);
      this.buildPrompts();
    });
  }

  // ── Session management ─────────────────────────────────────────────────
  loadSessions(): void {
    this.adviceService.getSessions().subscribe({
      next: (sessions) => {
        this.sessions = sessions;
        if (sessions.length > 0 && this.activeSessionId === null) {
          this.selectSession(sessions[0].id);
        }
      },
      error: () => {},
    });
  }

  selectSession(id: number): void {
    this.activeSessionId = id;
    this.animateLastMessage = false;
    this.history = [];
    this.sidebarOpen = false;
    this.adviceService.getMessages(id).subscribe({
      next: (msgs) => { this.history = this.mapApiMessages(msgs); },
      error: () => {},
    });
  }

  startNewChat(): void {
    this.adviceService.createSession().subscribe({
      next: (session) => {
        this.sessions = [session, ...this.sessions];
        this.activeSessionId = session.id;
        this.history = [];
        this.sidebarOpen = false;
      },
      error: () => {},
    });
  }

  deleteSession(id: number): void {
    this.adviceService.deleteSession(id).subscribe({
      next: () => {
        this.sessions = this.sessions.filter(s => s.id !== id);
        if (this.activeSessionId === id) {
          this.history = [];
          this.activeSessionId = this.sessions[0]?.id ?? null;
          if (this.activeSessionId) {
            this.selectSession(this.activeSessionId);
          }
        }
      },
      error: () => {},
    });
  }

  // ── Memory management ──────────────────────────────────────────────────
  toggleMemoryPanel(): void {
    if (!this.memoryPanelOpen) {
      this.adviceService.getMemory().subscribe({
        next: (facts) => { this.memoryFacts = facts; },
        error: () => {},
      });
    }
    this.memoryPanelOpen = !this.memoryPanelOpen;
  }

  closeMemoryPanel(): void { this.memoryPanelOpen = false; }

  deleteMemoryFact(id: number): void {
    this.adviceService.deleteMemory(id).subscribe({
      next: () => { this.memoryFacts = this.memoryFacts.filter(f => f.id !== id); },
      error: () => {},
    });
  }

  // ── Quick prompts ──────────────────────────────────────────────────────
  setPrompt(prompt: string): void {
    this.chatForm.patchValue({ question: prompt });
    this.submit();
  }

  // ── Submit ─────────────────────────────────────────────────────────────
  submit(): void {
    if (this.chatForm.invalid) {
      this.chatForm.markAllAsTouched();
      return;
    }

    const { question, metricNames, days } = this.chatForm.getRawValue();
    this.isLoading = true;
    this.errorMessage = '';

    const pendingIndex = this.appendPendingMessage(question);

    this.adviceService
      .ask(question, metricNames?.length ? metricNames : undefined, days, this.language, this.activeSessionId ?? undefined)
      .pipe(finalize(() => {
        this.isLoading = false;
        this.chatForm.patchValue({ question: '' });
      }))
      .subscribe({
        next: (response) => {
          if (response.session_id && !this.activeSessionId) {
            this.activeSessionId = response.session_id;
            this.loadSessions();
          }
          this.handleResponse(question, response, pendingIndex);
        },
        error: (err) => {
          this.removePendingMessage(pendingIndex);
          this.errorMessage = err?.error?.detail ?? 'Failed to get advice. Please try again.';
        },
      });
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  private mapApiMessages(msgs: ChatSessionMessage[]): ChatMessage[] {
    const result: ChatMessage[] = [];
    for (let i = 0; i < msgs.length - 1; i += 2) {
      const userMsg = msgs[i];
      const aiMsg = msgs[i + 1];
      if (userMsg?.role === 'user' && aiMsg?.role === 'assistant') {
        result.push({
          question: userMsg.content,
          answer: aiMsg.content,
          metrics: [],
          disclaimer: true,
          timestamp: new Date(userMsg.created_at),
        });
      }
    }
    return result;
  }

  private handleResponse(question: string, response: AdviceResponseModel, pendingIndex: number): void {
    const updatedMessage: ChatMessage = {
      question,
      answer: this.normalizeAdviceAnswer(response.answer),
      metrics: response.usedMetrics,
      disclaimer: response.disclaimer,
      timestamp: this.history[pendingIndex]?.timestamp ?? new Date(),
    };
    this.animateLastMessage = true;
    this.upsertPendingMessage(pendingIndex, updatedMessage);
  }

  private appendPendingMessage(question: string): number {
    this.history = [...this.history, { question, answer: '', metrics: [], disclaimer: false, timestamp: new Date() }];
    return this.history.length - 1;
  }

  private upsertPendingMessage(index: number, message: ChatMessage): void {
    if (index < 0 || index >= this.history.length) { this.history = [...this.history, message]; return; }
    const next = [...this.history];
    next[index] = message;
    this.history = next;
  }

  private removePendingMessage(index: number): void {
    if (index < 0 || index >= this.history.length) return;
    this.history = this.history.filter((_, i) => i !== index);
  }

  private buildPrompts(): void {
    const copy = this.promptCopy[this.language] ?? this.promptCopy.es;
    const metricPrompts = this.availableMetrics.slice(0, 3).map(m => copy.metricTemplate.replace('{{metric}}', m));
    this.quickPrompts = [...copy.base, ...metricPrompts].slice(0, 6);
  }

  private getDisplayName(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
  }

  private sortByRecent(items: V2AnalyteItemResponse[]): V2AnalyteItemResponse[] {
    return [...items].sort((a, b) => this.dateTimestamp(b.last_date) - this.dateTimestamp(a.last_date));
  }

  private dateTimestamp(v: string | null): number {
    if (!v) return 0;
    const ts = Date.parse(v);
    return Number.isFinite(ts) ? ts : 0;
  }

  private normalizeAdviceAnswer(answer: string | null | undefined): string {
    const text = (answer ?? '').trim();
    return text || 'No pude generar un resumen util con los datos actuales. Intenta con una pregunta mas especifica.';
  }
}
