import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';

import { GlassCardComponent } from '../glass-card/glass-card.component';
import { ChatMessage } from '../../../core/models/chat.model';

@Component({
  selector: 'app-chat-shell',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslateModule, GlassCardComponent],
  templateUrl: './chat-shell.component.html',
  styleUrls: ['./chat-shell.component.scss'],
})
export class ChatShellComponent {
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

  @Input() history: ChatMessage[] = [];
  @Input() isLoading = false;
  @Input() form!: FormGroup;
  @Input() quickPrompts: string[] = [];

  @Output() submitMessage = new EventEmitter<void>();
  @Output() selectPrompt = new EventEmitter<string>();

  onSubmit(): void {
    this.submitMessage.emit();
  }

  onPrompt(prompt: string): void {
    this.selectPrompt.emit(prompt);
  }

  get questionControl() {
    return this.form?.get('question');
  }
}
