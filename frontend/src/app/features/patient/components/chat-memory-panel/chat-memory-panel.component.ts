import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { PatientMemoryFact } from '../../../../core/models/chat-session.model';

@Component({
  selector: 'app-chat-memory-panel',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './chat-memory-panel.component.html',
  styleUrls: ['./chat-memory-panel.component.scss'],
})
export class ChatMemoryPanelComponent {
  @Input() facts: PatientMemoryFact[] = [];
  @Output() deleteFact = new EventEmitter<number>();
  @Output() close = new EventEmitter<void>();

  readonly categories = ['medical', 'preference', 'recommendation'] as const;

  factsForCategory(cat: string): PatientMemoryFact[] {
    return this.facts.filter(f => f.category === cat);
  }

  categoryKey(cat: string): string {
    const map: Record<string, string> = {
      medical: 'chat.memoryMedical',
      preference: 'chat.memoryPreference',
      recommendation: 'chat.memoryRecommendation',
    };
    return map[cat] ?? cat;
  }

  onDelete(id: number): void { this.deleteFact.emit(id); }
  onClose(): void { this.close.emit(); }
}
