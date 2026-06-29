import { Injectable, Signal, signal } from '@angular/core';

export type ThemeName = 'dark' | 'light';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly storageKey = 'medic-theme';
  private readonly defaultTheme: ThemeName = 'dark';
  private readonly isBrowser = typeof window !== 'undefined' && typeof document !== 'undefined';

  private preferredTheme: ThemeName = this.loadInitialTheme();
  private overrideTheme: ThemeName | null = null;
  private readonly themeSignal = signal<ThemeName>(this.preferredTheme);
  readonly theme: Signal<ThemeName> = this.themeSignal.asReadonly();

  constructor() {
    if (this.isBrowser) {
      this.applyTheme(this.themeSignal());
    }
  }

  setTheme(theme: ThemeName): void {
    this.preferredTheme = theme;
    if (this.isBrowser) {
      localStorage.setItem(this.storageKey, theme);
    }
    this.syncTheme();
  }

  toggleTheme(): void {
    this.setTheme(this.preferredTheme === 'dark' ? 'light' : 'dark');
  }

  setThemeOverride(theme: ThemeName | null): void {
    this.overrideTheme = theme;
    this.syncTheme();
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

  private syncTheme(): void {
    const effectiveTheme = this.overrideTheme ?? this.preferredTheme;
    this.themeSignal.set(effectiveTheme);
    if (this.isBrowser) {
      this.applyTheme(effectiveTheme);
    }
  }
}
