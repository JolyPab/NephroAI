import { CommonModule } from '@angular/common';
import { Component, EventEmitter, HostBinding, Input, Output } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';
import { GlassButtonDirective } from '../glass-button/glass-button.directive';

type ToolbarAccent = 'default' | 'doctor';

@Component({
  selector: 'app-glass-toolbar',
  standalone: true,
  imports: [CommonModule, GlassButtonDirective, TranslateModule],
  templateUrl: './glass-toolbar.component.html',
  styleUrls: ['./glass-toolbar.component.scss'],
})
export class GlassToolbarComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() showBack = false;
  @Input() compact = false;
  @Input() accent: ToolbarAccent = 'default';
  @Input() logoSrc = 'assets/brand/logo.png';
  @Input() brandTextKey = 'COMMON.BRAND_NAME';

  logoError = false;

  @HostBinding('class.glass-toolbar--accent-doctor') get doctorAccent(): boolean {
    return this.accent === 'doctor';
  }

  @Output() back = new EventEmitter<void>();

  handleBack(): void {
    this.back.emit();
  }

  handleLogoError(): void {
    this.logoError = true;
  }
}
