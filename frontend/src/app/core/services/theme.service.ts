import { Injectable, Signal, signal } from '@angular/core';

export type ThemeName = 'dark' | 'light';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly storageKey = 'medic-theme';
  private readonly defaultTheme: ThemeName = 'dark';
  private readonly isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';

  private readonly themeSignal = signal<ThemeName>(this.loadInitialTheme());
  readonly theme: Signal<ThemeName> = this.themeSignal.asReadonly();

  constructor() {
    if (this.isBrowser) {
      this.applyTheme(this.themeSignal());
    }
  }

  setTheme(theme: ThemeName): void {
    if (theme === this.themeSignal()) {
      return;
    }
    this.themeSignal.set(theme);
    if (this.isBrowser) {
      localStorage.setItem(this.storageKey, theme);
      this.applyTheme(theme);
    }
  }

  toggleTheme(): void {
    this.setTheme(this.themeSignal() === 'dark' ? 'light' : 'dark');
  }

  private loadInitialTheme(): ThemeName {
    if (!this.isBrowser) {
      return this.defaultTheme;
    }

    const stored = localStorage.getItem(this.storageKey) as ThemeName | null;
    if (stored === 'dark' || stored === 'light') {
      return stored;
    }

    const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ?? true;
    return prefersDark ? 'dark' : 'light';
  }

  private applyTheme(theme: ThemeName): void {
    if (!this.isBrowser) {
      return;
    }
    document.documentElement.setAttribute('data-theme', theme);
    document.body?.setAttribute('data-theme', theme);
    document.documentElement.style.setProperty('color-scheme', theme);
  }
}
