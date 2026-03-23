import { Component, EventEmitter, Input, OnChanges, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { ChatSessionSummary } from '../../../../core/models/chat-session.model';

interface SessionGroup {
  labelKey: string;
  sessions: ChatSessionSummary[];
}

@Component({
  selector: 'app-chat-sidebar',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './chat-sidebar.component.html',
  styleUrls: ['./chat-sidebar.component.scss'],
})
export class ChatSidebarComponent implements OnChanges {
  @Input() sessions: ChatSessionSummary[] = [];
  @Input() activeSessionId: number | null = null;

  @Output() selectSession = new EventEmitter<number>();
  @Output() newChat = new EventEmitter<void>();
  @Output() deleteSession = new EventEmitter<number>();

  groups: SessionGroup[] = [];

  ngOnChanges(): void {
    this.groups = this.buildGroups(this.sessions);
  }

  private buildGroups(sessions: ChatSessionSummary[]): SessionGroup[] {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfWeek = startOfToday - (now.getDay() || 7) * 86400000 + 86400000;
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).getTime();

    const groups: Record<string, ChatSessionSummary[]> = {
      today: [], thisWeek: [], thisMonth: [], earlier: [],
    };

    for (const s of sessions) {
      const ts = s.updated_at ? Date.parse(s.updated_at) : 0;
      if (ts >= startOfToday) groups['today'].push(s);
      else if (ts >= startOfWeek) groups['thisWeek'].push(s);
      else if (ts >= startOfMonth) groups['thisMonth'].push(s);
      else groups['earlier'].push(s);
    }

    return [
      { labelKey: 'chat.today', sessions: groups['today'] },
      { labelKey: 'chat.thisWeek', sessions: groups['thisWeek'] },
      { labelKey: 'chat.thisMonth', sessions: groups['thisMonth'] },
      { labelKey: 'chat.earlier', sessions: groups['earlier'] },
    ].filter(g => g.sessions.length > 0);
  }

  onSelect(id: number): void { this.selectSession.emit(id); }
  onNew(): void { this.newChat.emit(); }
  onDelete(event: Event, id: number): void {
    event.stopPropagation();
    this.deleteSession.emit(id);
  }

  displayTitle(s: ChatSessionSummary): string {
    return (s.title?.trim() || s.preview?.slice(0, 40) || '...') as string;
  }
}
