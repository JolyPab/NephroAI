import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';

type FunnelEvent = 'landing_view' | 'auth_view';

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly api = inject(ApiService);
  private readonly anonymousId = this.getAnonymousId();

  track(event: FunnelEvent): void {
    if (typeof window === 'undefined') {
      return;
    }
    const onceKey = `nephroai.analytics.${event}.${window.location.pathname}`;
    if (sessionStorage.getItem(onceKey)) {
      return;
    }

    const query = new URLSearchParams(window.location.search);
    this.api
      .post('/analytics/event', {
        event,
        anonymous_id: this.anonymousId,
        path: window.location.pathname,
        source: query.get('utm_source'),
        medium: query.get('utm_medium'),
        campaign: query.get('utm_campaign'),
        click_id: query.get('fbclid') || query.get('gclid'),
      })
      .subscribe({
        next: () => sessionStorage.setItem(onceKey, '1'),
        error: () => undefined,
      });
  }

  private getAnonymousId(): string {
    if (typeof window === 'undefined') {
      return 'server-render';
    }
    const key = 'nephroai.analytics.id';
    const existing = localStorage.getItem(key);
    if (existing) {
      return existing;
    }
    const generated =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem(key, generated);
    return generated;
  }
}
