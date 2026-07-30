import { Component, HostListener, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';

import { BillingService } from '../../../../core/services/billing.service';

@Component({
  selector: 'app-patient-shell',
  standalone: false,
  templateUrl: './patient-shell.component.html',
  styleUrls: ['./patient-shell.component.scss'],
})
export class PatientShellComponent implements OnInit {
  private static readonly TRIAL_WELCOME_KEY = 'nephroai.showTrialWelcome';

  private readonly router = inject(Router);
  private readonly billing = inject(BillingService);

  showTrialWelcome = false;
  checkoutBusy = false;
  checkoutError = '';

  ngOnInit(): void {
    if (sessionStorage.getItem(PatientShellComponent.TRIAL_WELCOME_KEY) !== 'true') {
      return;
    }

    this.billing.getSubscription().subscribe({
      next: (subscription) => {
        sessionStorage.removeItem(PatientShellComponent.TRIAL_WELCOME_KEY);
        this.showTrialWelcome = !['active', 'trialing'].includes(subscription.status);
      },
      error: () => {
        sessionStorage.removeItem(PatientShellComponent.TRIAL_WELCOME_KEY);
      },
    });
  }

  get isChat(): boolean {
    return this.router.url.includes('/chat');
  }

  closeTrialWelcome(): void {
    if (!this.checkoutBusy) {
      this.showTrialWelcome = false;
    }
  }

  startTrial(): void {
    if (this.checkoutBusy) {
      return;
    }

    this.checkoutBusy = true;
    this.checkoutError = '';
    this.billing.createCheckoutSession('monthly').subscribe({
      next: (session) => {
        window.location.href = session.checkout_url;
      },
      error: (err) => {
        this.checkoutError = err?.error?.detail ?? 'No pudimos abrir el pago. Inténtalo de nuevo.';
        this.checkoutBusy = false;
      },
    });
  }

  uploadFirstDocument(): void {
    this.showTrialWelcome = false;
    void this.router.navigate(['/patient/upload']);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closeTrialWelcome();
  }
}
