import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';

export interface AdminFunnel {
  visitors: number;
  access: number;
  registered: number;
  verified: number;
  activated: number;
  checkout: number;
  subscriptions: number;
}

export interface AdminSeriesPoint {
  date: string;
  registered: number;
  verified: number;
  activated: number;
}

export interface AdminRecentUser {
  id: number;
  email: string;
  registeredAt: string;
  verifiedAt: string | null;
  firstUploadAt: string | null;
  firstChatAt: string | null;
  subscription: string;
}

export interface AdminOverview {
  period: { from: string; to: string };
  totals: {
    users: number;
    activeSubscriptions: number;
    revenue: Record<string, number>;
  };
  funnel: AdminFunnel;
  series: AdminSeriesPoint[];
  recentUsers: AdminRecentUser[];
  system: {
    database: string;
    errors15m: number;
    generatedAt: string;
    lastEventAt: string | null;
    trackingSince: string | null;
  };
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly api = inject(ApiService);

  access(): Observable<{ allowed: boolean }> {
    return this.api.get('/admin/access');
  }

  overview(dateFrom: string, dateTo: string): Observable<AdminOverview> {
    return this.api.get('/admin/overview', {
      date_from: dateFrom,
      date_to: dateTo,
    });
  }
}
