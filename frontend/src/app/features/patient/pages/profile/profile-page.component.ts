import { Component, DestroyRef, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { AuthService } from '../../../../core/services/auth.service';
import { LanguageService } from '../../../../core/services/language.service';
import { ThemeService } from '../../../../core/services/theme.service';

@Component({
  selector: 'app-patient-profile-page',
  standalone: false,
  templateUrl: './profile-page.component.html',
  styleUrls: ['./profile-page.component.scss'],
})
export class PatientProfilePageComponent {
  private readonly auth = inject(AuthService);
  private readonly themeService = inject(ThemeService);
  private readonly fb = inject(FormBuilder);
  private readonly languageService = inject(LanguageService);
  private readonly destroyRef = inject(DestroyRef);
  readonly user = this.auth.user;
  readonly theme = this.themeService.theme;
  currentLang = this.languageService.currentLang;

  readonly nameForm = this.fb.nonNullable.group({
    full_name: [this.user()?.full_name ?? '', [Validators.required, Validators.minLength(2)]],
  });
  savingName = false;
  nameMessage = '';
  nameError = '';

  constructor() {
    this.languageService
      .onLangChange()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((lang) => {
        this.currentLang = lang;
      });
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  setTheme(theme: 'dark' | 'light'): void {
    this.themeService.setTheme(theme);
  }

  setLanguage(lang: string): void {
    this.languageService.setLanguage(lang);
    this.currentLang = this.languageService.currentLang;
  }

  saveName(): void {
    if (this.nameForm.invalid) {
      this.nameForm.markAllAsTouched();
      return;
    }
    this.savingName = true;
    this.nameMessage = '';
    this.nameError = '';
    const { full_name } = this.nameForm.getRawValue();
    this.auth.updateProfile({ full_name }).subscribe({
      next: () => {
        this.savingName = false;
        this.nameMessage = 'profile.nameSaved';
      },
      error: (err) => {
        this.nameError = err?.error?.detail ?? 'Failed to update name.';
        this.savingName = false;
      },
    });
  }
}
