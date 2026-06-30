import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';

export interface BillingSubscription {
  status: string;
  provider?: string | null;
  current_period_end?: string | null;
  trial_end?: string | null;
  trial_available?: boolean;
}

export interface CheckoutSession {
  checkout_url: string;
  session_id: string;
}

export interface PortalSession {
  portal_url: string;
}

@Injectable({ providedIn: 'root' })
export class BillingService {
  private readonly api = inject(ApiService);

  getSubscription(): Observable<BillingSubscription> {
    return this.api.get<BillingSubscription>('/billing/subscription');
  }

  createCheckoutSession(interval: 'monthly' | 'yearly' = 'monthly'): Observable<CheckoutSession> {
    return this.api.post<CheckoutSession>('/billing/checkout-session', { interval });
  }

  createPortalSession(): Observable<PortalSession> {
    return this.api.post<PortalSession>('/billing/portal-session', {});
  }
}
