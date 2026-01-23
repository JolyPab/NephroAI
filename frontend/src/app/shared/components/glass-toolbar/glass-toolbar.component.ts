import { CommonModule } from '@angular/common';
import { Component, EventEmitter, HostBinding, Input, Output, computed, inject } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';
import { GlassButtonDirective } from '../glass-button/glass-button.directive';
import { ThemeService } from '../../../core/services/theme.service';

type ToolbarAccent = 'default' | 'doctor';

@Component({
  selector: 'app-glass-toolbar',
  standalone: true,
  imports: [CommonModule, GlassButtonDirective, TranslateModule],
  templateUrl: './glass-toolbar.component.html',
  styleUrls: ['./glass-toolbar.component.scss'],
})
export class GlassToolbarComponent {
  private readonly themeService = inject(ThemeService);
  readonly theme = this.themeService.theme;
  readonly themeLogoSrc = computed(() =>
    this.theme() === 'dark' ? 'assets/brand/logoDark.png' : 'assets/brand/logoWhite.png'
  );

  @Input() title = '';
  @Input() subtitle = '';
  @Input() showBack = false;
  @Input() compact = false;
  @Input() accent: ToolbarAccent = 'default';
  @Input() logoSrc = '';
  @Input() brandTextKey = 'COMMON.BRAND_NAME';

  logoError = false;

  @HostBinding('class.glass-toolbar--accent-doctor') get doctorAccent(): boolean {
    return this.accent === 'doctor';
  }

  @Output() back = new EventEmitter<void>();

  get resolvedLogoSrc(): string {
    return this.logoSrc?.trim() || this.themeLogoSrc();
  }

  handleBack(): void {
    this.back.emit();
  }

  handleLogoError(): void {
    this.logoError = true;
  }
}
