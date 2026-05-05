import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';

import { ChatMessage } from '../../../core/models/chat.model';

@Component({
  selector: 'app-chat-shell',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslateModule],
  templateUrl: './chat-shell.component.html',
  styleUrls: ['./chat-shell.component.scss'],
})
export class ChatShellComponent implements OnChanges, OnDestroy {
  @Input() titleKey = 'chat.title';
  @Input() subtitleKey = 'chat.subtitle';
  @Input() subtitleParams: Record<string, unknown> = {};
  @Input() secureKey = 'chat.secure';
  @Input() emptyKey = 'chat.empty';
  @Input() placeholderKey = 'chat.questionPh';
  @Input() minCharsKey = 'chat.minChars';
  @Input() youKey = 'chat.you';
  @Input() aiKey = 'chat.ai';
  @Input() disclaimerKey = 'chat.disclaimer';
  @Input() thinkingKey = 'chat.thinking';

  @Input() history: ChatMessage[] = [];
  @Input() isLoading = false;
  @Input() animateLastMessage = false;
  @Input() form!: FormGroup;
  @Input() quickPrompts: string[] = [];
  displayedAnswers: string[] = [];

  @ViewChild('chatWindow') private chatWindowRef?: ElementRef<HTMLDivElement>;

  @Output() submitMessage = new EventEmitter<void>();
  @Output() selectPrompt = new EventEmitter<string>();
  private typingInterval: ReturnType<typeof setInterval> | null = null;
  private typingTargetIndex: number | null = null;
  private readonly typedMessageKeys = new Set<string>();
  private prevHistoryLength = 0;

  onSubmit(): void {
    this.submitMessage.emit();
  }
  formatBubbleTime(value: string | Date | null | undefined): string {
    if (!value) return '';

    const raw = value instanceof Date ? value.toISOString() : String(value);
    const normalized = this.normalizeTimestamp(raw);
    const date = new Date(normalized);

    if (Number.isNaN(date.getTime())) return '';

    return new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }

  private normalizeTimestamp(value: string): string {
    const trimmed = value.trim();

    if (/[zZ]$|[+-]\d{2}:\d{2}$/.test(trimmed)) {
      return trimmed;
    }

    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(trimmed)) {
      return `${trimmed}Z`;
    }

    return trimmed;
  }
  onPrompt(prompt: string): void {
    this.selectPrompt.emit(prompt);
  }

  get questionControl() {
    return this.form?.get('question');
  }

  renderMessageAsHtml(value: string | null | undefined): string {
    const markdown = (value ?? '').replace(/\r\n?/g, '\n').trim();
    if (!markdown) {
      return '';
    }

    const lines = markdown.split('\n');
    const htmlParts: string[] = [];
    let listType: 'ul' | 'ol' | null = null;
    let inCodeBlock = false;
    let codeLines: string[] = [];

    const closeList = () => {
      if (!listType) {
        return;
      }
      htmlParts.push(`</${listType}>`);
      listType = null;
    };

    const closeCodeBlock = () => {
      const body = this.escapeHtml(codeLines.join('\n'));
      htmlParts.push(`<pre><code>${body}</code></pre>`);
      codeLines = [];
      inCodeBlock = false;
    };

    for (const rawLine of lines) {
      const trimmed = rawLine.trim();

      if (trimmed.startsWith('```')) {
        closeList();
        if (inCodeBlock) {
          closeCodeBlock();
        } else {
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeLines.push(rawLine);
        continue;
      }

      if (!trimmed) {
        closeList();
        continue;
      }

      const headingMatch = /^#{1,6}\s+(.*)$/.exec(trimmed);
      if (headingMatch) {
        closeList();
        htmlParts.push(`<h4>${this.renderInlineMarkdown(headingMatch[1])}</h4>`);
        continue;
      }

      const unorderedMatch = /^[-*]\s+(.*)$/.exec(trimmed);
      if (unorderedMatch) {
        if (listType !== 'ul') {
          closeList();
          listType = 'ul';
          htmlParts.push('<ul>');
        }
        htmlParts.push(`<li>${this.renderInlineMarkdown(unorderedMatch[1])}</li>`);
        continue;
      }

      const orderedMatch = /^\d+[.)]\s+(.*)$/.exec(trimmed);
      if (orderedMatch) {
        if (listType !== 'ol') {
          closeList();
          listType = 'ol';
          htmlParts.push('<ol>');
        }
        htmlParts.push(`<li>${this.renderInlineMarkdown(orderedMatch[1])}</li>`);
        continue;
      }

      closeList();
      htmlParts.push(`<p>${this.renderInlineMarkdown(trimmed)}</p>`);
    }

    if (inCodeBlock) {
      closeCodeBlock();
    }
    closeList();
    return htmlParts.join('');
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['history']) {
      this.syncDisplayedAnswers();
      this.scrollToBottomSoon();
    }
    if (changes['isLoading']) {
      this.scrollToBottomSoon();
    }
  }

  ngOnDestroy(): void {
    this.stopTyping();
  }

  private syncDisplayedAnswers(): void {
    if (!this.history.length) {
      this.stopTyping();
      this.displayedAnswers = [];
      this.prevHistoryLength = 0;
      return;
    }

    this.displayedAnswers = this.displayedAnswers.slice(0, this.history.length);
    while (this.displayedAnswers.length < this.history.length) {
      this.displayedAnswers.push('');
    }

    const lastIndex = this.history.length - 1;
    for (let i = 0; i < lastIndex; i += 1) {
      const msg = this.history[i];
      this.displayedAnswers[i] = msg.answer ?? '';
      this.typedMessageKeys.add(this.messageKey(i));
    }

    const lastMessage = this.history[lastIndex];
    const finalAnswer = lastMessage.answer ?? '';
    if (!finalAnswer) {
      this.displayedAnswers[lastIndex] = '';
      if (this.typingTargetIndex === lastIndex) {
        this.stopTyping();
      }
      return;
    }

    const key = this.messageKey(lastIndex);
    if (this.typedMessageKeys.has(key) || this.displayedAnswers[lastIndex] === finalAnswer) {
      this.displayedAnswers[lastIndex] = finalAnswer;
      this.prevHistoryLength = this.history.length;
      return;
    }

    this.prevHistoryLength = this.history.length;
    if (!this.animateLastMessage) {
      this.displayedAnswers[lastIndex] = finalAnswer;
      this.typedMessageKeys.add(key);
      return;
    }

    this.startTyping(lastIndex, finalAnswer, key);
  }

  private startTyping(index: number, text: string, key: string): void {
    this.stopTyping();
    this.typingTargetIndex = index;
    this.displayedAnswers[index] = '';

    let cursor = 0;
    const step = text.length > 480 ? 6 : text.length > 220 ? 4 : 2;
    this.typingInterval = setInterval(() => {
      cursor = Math.min(text.length, cursor + step);
      this.displayedAnswers[index] = text.slice(0, cursor);
      this.scrollToBottom();
      if (cursor >= text.length) {
        this.typedMessageKeys.add(key);
        this.stopTyping();
      }
    }, 16);
  }

  private stopTyping(): void {
    if (this.typingInterval) {
      clearInterval(this.typingInterval);
      this.typingInterval = null;
    }
    this.typingTargetIndex = null;
  }

  private messageKey(index: number): string {
    const message = this.history[index];
    const tsRaw = message?.timestamp;
    const ts = tsRaw instanceof Date ? tsRaw.getTime() : Date.parse(String(tsRaw ?? ''));
    return `${Number.isFinite(ts) ? ts : index}:${message?.question ?? ''}:${message?.answer ?? ''}`;
  }

  private scrollToBottomSoon(): void {
    setTimeout(() => this.scrollToBottom(), 0);
  }

  private scrollToBottom(): void {
    const container = this.chatWindowRef?.nativeElement;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  }

  private renderInlineMarkdown(text: string): string {
    let html = this.escapeHtml(text);
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    html = html.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
    html = html.replace(/(^|[^_])_([^_]+)_/g, '$1<em>$2</em>');
    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    );
    return html;
  }

  private escapeHtml(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}


