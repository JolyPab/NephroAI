import { Component, OnInit, inject } from '@angular/core';

import {
  AdminFunnel,
  AdminOverview,
  AdminSeriesPoint,
  AdminService,
} from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';

type SeriesKey = 'registered' | 'verified' | 'activated';

@Component({
  selector: 'app-admin-dashboard-page',
  standalone: false,
  templateUrl: './admin-dashboard-page.component.html',
  styleUrl: './admin-dashboard-page.component.scss',
})
export class AdminDashboardPageComponent implements OnInit {
  private readonly admin = inject(AdminService);
  private readonly auth = inject(AuthService);

  readonly today = this.toDateInput(new Date());
  dateTo = this.today;
  dateFrom = this.toDateInput(new Date(Date.now() - 7 * 86_400_000));
  overview: AdminOverview | null = null;
  loading = true;
  error = '';
  navOpen = false;

  readonly funnelLabels: Array<{ key: keyof AdminFunnel; label: string }> = [
    { key: 'visitors', label: 'Visitantes' },
    { key: 'access', label: 'Acceso' },
    { key: 'registered', label: 'Registrados' },
    { key: 'verified', label: 'Verificados' },
    { key: 'activated', label: 'Activados' },
    { key: 'checkout', label: 'Checkout' },
    { key: 'subscriptions', label: 'Suscripciones' },
  ];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    if (!this.dateFrom || !this.dateTo || this.dateFrom > this.dateTo) {
      this.error = 'Selecciona un periodo válido.';
      return;
    }
    this.loading = true;
    this.error = '';
    this.admin.overview(this.dateFrom, this.dateTo).subscribe({
      next: (overview) => {
        this.overview = overview;
        this.loading = false;
      },
      error: () => {
        this.error = 'No se pudieron actualizar los datos.';
        this.loading = false;
      },
    });
  }

  logout(): void {
    this.auth.logout().subscribe({ complete: () => location.assign('/auth') });
  }

  funnelWidth(key: keyof AdminFunnel): number {
    if (!this.overview) return 0;
    const values = Object.values(this.overview.funnel);
    const denominator = Math.max(this.overview.funnel.visitors, ...values, 1);
    return Math.max((this.overview.funnel[key] / denominator) * 100, this.overview.funnel[key] ? 2 : 0);
  }

  funnelPercent(key: keyof AdminFunnel): string {
    if (!this.overview) return '0%';
    const denominator = this.overview.funnel.visitors || 1;
    return `${((this.overview.funnel[key] / denominator) * 100).toFixed(key === 'visitors' ? 0 : 2)}%`;
  }

  chartPath(key: SeriesKey): string {
    const series = this.overview?.series ?? [];
    if (!series.length) return '';
    const max = this.chartMax(series);
    return series
      .map((point, index) => {
        const x = series.length === 1 ? 320 : 24 + (index * 592) / (series.length - 1);
        const y = 166 - (point[key] / max) * 132;
        return `${index ? 'L' : 'M'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');
  }

  chartX(index: number): number {
    const length = this.overview?.series.length ?? 1;
    return length === 1 ? 320 : 24 + (index * 592) / (length - 1);
  }

  formatDay(value: string): string {
    return new Intl.DateTimeFormat('es-MX', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
      new Date(`${value}T00:00:00Z`),
    );
  }

  formatDate(value: string | null): string {
    if (!value) return '—';
    return new Intl.DateTimeFormat('es-MX', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  }

  subscriptionLabel(status: string): string {
    const labels: Record<string, string> = {
      none: 'Sin suscripción',
      inactive: 'Checkout iniciado',
      active: 'Activa',
      trialing: 'Prueba',
      canceled: 'Cancelada',
      past_due: 'Pago pendiente',
    };
    return labels[status] ?? status;
  }

  private chartMax(series: AdminSeriesPoint[]): number {
    return Math.max(1, ...series.flatMap((point) => [point.registered, point.verified, point.activated]));
  }

  private toDateInput(date: Date): string {
    return date.toISOString().slice(0, 10);
  }
}
