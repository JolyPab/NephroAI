import { CommonModule } from '@angular/common';
import { Component, EventEmitter, HostBinding, Input, Output } from '@angular/core';
import { GlassButtonDirective } from '../glass-button/glass-button.directive';

type ToolbarAccent = 'default' | 'doctor';

@Component({
  selector: 'app-glass-toolbar',
  standalone: true,
  imports: [CommonModule, GlassButtonDirective],
  templateUrl: './glass-toolbar.component.html',
  styleUrls: ['./glass-toolbar.component.scss'],
})
export class GlassToolbarComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() showBack = false;
  @Input() compact = false;
  @Input() accent: ToolbarAccent = 'default';

  @HostBinding('class.glass-toolbar--accent-doctor') get doctorAccent(): boolean {
    return this.accent === 'doctor';
  }

  @Output() back = new EventEmitter<void>();

  handleBack(): void {
    this.back.emit();
  }
}
