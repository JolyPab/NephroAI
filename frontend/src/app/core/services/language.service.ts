import { Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { map, Observable } from 'rxjs';

const SUPPORTED_LANGS = ['es', 'en'] as const;
type SupportedLang = (typeof SUPPORTED_LANGS)[number];

@Injectable({ providedIn: 'root' })
export class LanguageService {
  private readonly storageKey = 'lang';

  constructor(private readonly translate: TranslateService) {}

  init(): void {
    this.translate.addLangs([...SUPPORTED_LANGS]);
    this.translate.setDefaultLang('en');

    const stored = this.loadStoredLang();
    const nextLang = this.isSupportedLang(stored) ? stored : 'es';
    this.translate.use(nextLang);
    localStorage.setItem(this.storageKey, nextLang);
  }

  get currentLang(): SupportedLang {
    const current = this.translate.currentLang;
    if (this.isSupportedLang(current)) {
      return current;
    }
    const fallback = this.translate.defaultLang;
    return this.isSupportedLang(fallback) ? fallback : 'es';
  }

  get supportedLangs(): SupportedLang[] {
    return [...SUPPORTED_LANGS];
  }

  setLanguage(lang: string): void {
    const next = this.isSupportedLang(lang) ? lang : 'es';
    this.translate.use(next);
    localStorage.setItem(this.storageKey, next);
  }

  onLangChange(): Observable<SupportedLang> {
    return this.translate.onLangChange.pipe(map((event) => (this.isSupportedLang(event.lang) ? event.lang : 'es')));
  }

  private loadStoredLang(): string | null {
    return localStorage.getItem(this.storageKey);
  }

  private isSupportedLang(value: string | null | undefined): value is SupportedLang {
    return SUPPORTED_LANGS.includes(value as SupportedLang);
  }
}
