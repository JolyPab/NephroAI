import { AfterViewInit, Component, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';

import {
  AuthService,
  SocialProviderConfig,
} from '../../../../core/services/auth.service';
import { SocialAuthSdkService } from '../../../../core/services/social-auth-sdk.service';
import { AnalyticsService } from '../../../../core/services/analytics.service';
import { User } from '../../../../core/models/user.model';

type AuthMode =
  | 'login'
  | 'register'
  | 'social-register'
  | 'verify'
  | 'forgot'
  | 'reset-verify'
  | 'reset-password';

type SocialProvider = 'google' | 'facebook';

interface PendingSocialRegistration {
  provider: SocialProvider;
  credential: string;
}

@Component({
  selector: 'app-auth-page',
  standalone: false,
  templateUrl: './auth-page.component.html',
  styleUrls: ['./auth-page.component.scss'],
})
export class AuthPageComponent implements OnInit, AfterViewInit {
  private static readonly TRIAL_WELCOME_KEY = 'nephroai.showTrialWelcome';
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly analytics = inject(AnalyticsService);
  private readonly socialSdk = inject(SocialAuthSdkService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);

  private googleButtonHost?: HTMLElement;

  @ViewChild('googleButton')
  set googleButton(element: ElementRef<HTMLElement> | undefined) {
    this.googleButtonHost = element?.nativeElement;
    if (!this.googleButtonHost) {
      this.googleReady = false;
      return;
    }
    if (this.googleButtonHost && this.socialConfig?.googleClientId) {
      this.initializeGoogleProvider(this.socialConfig.googleClientId);
    }
  }

  mode: AuthMode = 'login';
  isSubmitting = false;
  errorMessage = '';
  infoMessage = '';
  pendingVerificationEmail = '';
  pendingResetEmail = '';
  resetToken = '';
  socialConfig: SocialProviderConfig | null = null;
  googleReady = false;
  facebookReady = false;
  socialProviderInProgress: 'google' | 'facebook' | null = null;
  private pendingSocialRegistration: PendingSocialRegistration | null = null;

  readonly loginForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  readonly registerForm = this.fb.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', [Validators.required]],
    role: ['PATIENT'],
  });

  readonly socialRegisterForm = this.fb.nonNullable.group({
    role: ['PATIENT'],
  });

  readonly verifyForm = this.fb.nonNullable.group({
    code: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
  });

  readonly forgotForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  readonly resetPasswordForm = this.fb.nonNullable.group({
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', [Validators.required]],
  });

  ngOnInit(): void {
    this.analytics.track('auth_view');
    this.applyAuthQueryParams();
    this.auth.loadProfile().subscribe((user) => {
      if (user) {
        this.redirectAfterAuth(user);
      }
    });
  }

  ngAfterViewInit(): void {
    this.auth.getSocialProviderConfig().subscribe({
      next: (config) => {
        this.socialConfig = config;
        this.initializeSocialProviders(config);
      },
      error: () => {
        this.socialConfig = null;
      },
    });
  }

  get socialProvidersVisible(): boolean {
    return !!(this.socialConfig?.googleClientId || this.socialConfig?.facebookAppId);
  }

  toggleMode(): void {
    this.mode = this.mode === 'login' ? 'register' : 'login';
    this.pendingSocialRegistration = null;
    this.errorMessage = '';
    this.infoMessage = '';
    this.pendingVerificationEmail = '';
    this.verifyForm.reset();
  }

  submitSocialRegistration(): void {
    const pending = this.pendingSocialRegistration;
    if (!pending || this.isSubmitting) {
      return;
    }

    this.socialProviderInProgress = pending.provider;
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    this.auth.socialAuth({
      provider: pending.provider,
      credential: pending.credential,
      action: 'register',
      is_doctor: this.socialRegisterForm.getRawValue().role === 'DOCTOR',
    }).subscribe({
      next: ({ user, isNewUser }) => this.handleSocialAuthSuccess(user, isNewUser),
      error: (err) => {
        this.errorMessage = this.getErrorMessage(err, 'ERRORS.AUTH_SOCIAL_FAILED');
        this.isSubmitting = false;
        this.socialProviderInProgress = null;
      },
      complete: () => {
        this.isSubmitting = false;
        this.socialProviderInProgress = null;
      },
    });
  }

  cancelSocialRegistration(): void {
    if (this.isSubmitting) {
      return;
    }
    this.pendingSocialRegistration = null;
    this.socialRegisterForm.reset({ role: 'PATIENT' });
    this.mode = 'login';
    this.errorMessage = '';
    this.infoMessage = '';
  }

  async startFacebookAuth(): Promise<void> {
    if (!this.facebookReady || this.isSubmitting) {
      return;
    }
    this.socialProviderInProgress = 'facebook';
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    try {
      const credential = await this.socialSdk.loginWithFacebook();
      if (!credential) {
        this.isSubmitting = false;
        this.socialProviderInProgress = null;
        return;
      }
      this.completeSocialAuth('facebook', credential);
    } catch {
      this.errorMessage = this.translate.instant('ERRORS.AUTH_SOCIAL_SDK_FAILED');
      this.isSubmitting = false;
      this.socialProviderInProgress = null;
    }
  }

  submitLogin(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    this.auth.login(this.loginForm.getRawValue()).subscribe({
      next: (user) => this.redirectAfterAuth(user),
      error: (err) => {
        const detail = err?.error?.detail;
        if (err?.status === 403 && detail?.code === 'email_not_verified') {
          this.pendingVerificationEmail = detail.email || this.loginForm.getRawValue().email;
          this.mode = 'verify';
          this.verifyForm.reset();
          this.infoMessage = this.translate.instant('AUTH.VERIFICATION_RESUMED', {
            email: this.pendingVerificationEmail,
          });
          this.errorMessage = '';
          this.isSubmitting = false;
          return;
        }
        this.errorMessage = err?.status === 401
          ? this.translate.instant('ERRORS.AUTH_LOGIN_FAILED')
          : this.getErrorMessage(err, 'ERRORS.AUTH_LOGIN_FAILED');
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  submitRegister(): void {
    if (this.registerForm.invalid || this.registerForm.value.password !== this.registerForm.value.confirmPassword) {
      this.registerForm.markAllAsTouched();
      if (this.registerForm.value.password !== this.registerForm.value.confirmPassword) {
        this.errorMessage = this.translate.instant('ERRORS.AUTH_PASSWORDS_MISMATCH');
      }
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    const { email, password, role, full_name } = this.registerForm.getRawValue();
    this.auth.register({ email, password, role, full_name }).subscribe({
      next: (response) => {
        this.pendingVerificationEmail = response.email;
        this.mode = 'verify';
        this.verifyForm.reset();
        this.infoMessage = this.translate.instant('AUTH.VERIFICATION_CODE_SENT', { email: response.email });
      },
      error: (err) => {
        this.errorMessage = this.getErrorMessage(err, 'ERRORS.AUTH_REGISTER_FAILED');
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  submitVerify(): void {
    if (this.verifyForm.invalid || !this.pendingVerificationEmail) {
      this.verifyForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    const { code } = this.verifyForm.getRawValue();
    this.auth.verifyEmail({ email: this.pendingVerificationEmail, code }).subscribe({
      next: (user) => {
        const isDoctor = user.role === 'DOCTOR' || user.is_doctor === true;
        if (!isDoctor) {
          sessionStorage.setItem(AuthPageComponent.TRIAL_WELCOME_KEY, 'true');
        }
        this.redirectAfterAuth(user);
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_VERIFY_FAILED');
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  resendCode(): void {
    if (!this.pendingVerificationEmail || this.isSubmitting) {
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    this.auth.resendEmailCode({ email: this.pendingVerificationEmail }).subscribe({
      next: (response) => {
        this.infoMessage = this.translate.instant('AUTH.VERIFICATION_CODE_SENT', { email: response.email });
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_RESEND_FAILED');
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  goToForgot(): void {
    this.mode = 'forgot';
    this.errorMessage = '';
    this.infoMessage = '';
    this.forgotForm.reset();
  }

  backToLogin(): void {
    this.mode = 'login';
    this.errorMessage = '';
    this.infoMessage = '';
    this.pendingResetEmail = '';
    this.resetToken = '';
    this.forgotForm.reset();
    this.verifyForm.reset();
    this.resetPasswordForm.reset();
  }

  submitForgot(): void {
    if (this.forgotForm.invalid) {
      this.forgotForm.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    const { email } = this.forgotForm.getRawValue();
    this.auth.forgotPassword({ email }).subscribe({
      next: () => {
        this.pendingResetEmail = email;
        this.mode = 'reset-verify';
        this.verifyForm.reset();
        this.infoMessage = this.translate.instant('AUTH.RESET_CODE_SENT', { email });
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_FORGOT_FAILED');
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  submitResetVerify(): void {
    if (this.verifyForm.invalid || !this.pendingResetEmail) {
      this.verifyForm.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    const { code } = this.verifyForm.getRawValue();
    this.auth.verifyResetCode({ email: this.pendingResetEmail, code }).subscribe({
      next: (resp) => {
        this.resetToken = resp.reset_token;
        this.mode = 'reset-password';
        this.resetPasswordForm.reset();
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_RESET_VERIFY_FAILED');
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  resendResetCode(): void {
    if (!this.pendingResetEmail || this.isSubmitting) return;
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    this.auth.forgotPassword({ email: this.pendingResetEmail }).subscribe({
      next: () => {
        this.infoMessage = this.translate.instant('AUTH.RESET_CODE_SENT', { email: this.pendingResetEmail });
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_FORGOT_FAILED');
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  submitResetPassword(): void {
    if (this.resetPasswordForm.invalid || !this.resetToken) {
      this.resetPasswordForm.markAllAsTouched();
      return;
    }
    const { password, confirmPassword } = this.resetPasswordForm.getRawValue();
    if (password !== confirmPassword) {
      this.errorMessage = this.translate.instant('ERRORS.RESET_PASSWORD_MISMATCH');
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    this.auth.resetPassword({ reset_token: this.resetToken, new_password: password }).subscribe({
      next: () => {
        this.pendingResetEmail = '';
        this.resetToken = '';
        this.mode = 'login';
        this.infoMessage = this.translate.instant('AUTH.RESET_PASSWORD_SUCCESS');
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.translate.instant('ERRORS.AUTH_RESET_PASSWORD_FAILED');
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  private applyAuthQueryParams(): void {
    const mode = this.route.snapshot.queryParamMap.get('mode');
    const email = this.route.snapshot.queryParamMap.get('email')?.trim();
    if (mode === 'register') {
      this.mode = 'register';
      this.errorMessage = '';
      this.infoMessage = '';
      return;
    }
    if (mode === 'reset-verify' && email) {
      this.mode = 'reset-verify';
      this.pendingResetEmail = email;
      this.verifyForm.reset();
      this.infoMessage = this.translate.instant('AUTH.RESET_LINK_OPENED', { email });
      this.errorMessage = '';
      return;
    }
    if (mode !== 'verify' || !email) {
      return;
    }
    this.mode = 'verify';
    this.pendingVerificationEmail = email;
    this.verifyForm.reset();
    this.infoMessage = this.translate.instant('AUTH.VERIFICATION_LINK_OPENED', { email });
    this.errorMessage = '';
  }

  private getErrorMessage(err: any, fallbackKey: string): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (detail && typeof detail.message === 'string') {
      return detail.message;
    }
    return this.translate.instant(fallbackKey);
  }

  private initializeSocialProviders(config: SocialProviderConfig): void {
    if (config.googleClientId) {
      this.initializeGoogleProvider(config.googleClientId);
    }

    if (config.facebookAppId) {
      this.socialSdk
        .initializeFacebook(config.facebookAppId, config.facebookApiVersion)
        .then(() => {
          this.facebookReady = true;
        })
        .catch(() => {
          this.facebookReady = false;
        });
    }
  }

  private initializeGoogleProvider(clientId: string): void {
    const host = this.googleButtonHost;
    if (!host || this.googleReady) {
      return;
    }

    this.socialSdk
      .renderGoogleButton(
        host,
        clientId,
        (credential) => this.completeSocialAuth('google', credential),
      )
      .then(() => {
        if (this.googleButtonHost === host) {
          this.googleReady = true;
        }
      })
      .catch(() => {
        if (this.googleButtonHost === host) {
          this.googleReady = false;
        }
      });
  }

  private completeSocialAuth(provider: SocialProvider, credential: string): void {
    if (this.mode !== 'login' && this.mode !== 'register') {
      return;
    }
    const action = this.mode;
    const isDoctor = action === 'register' && this.registerForm.getRawValue().role === 'DOCTOR';
    this.socialProviderInProgress = provider;
    this.isSubmitting = true;
    this.errorMessage = '';
    this.infoMessage = '';
    this.auth.socialAuth({
      provider,
      credential,
      action,
      is_doctor: isDoctor,
    }).subscribe({
      next: ({ user, isNewUser }) => this.handleSocialAuthSuccess(user, isNewUser),
      error: (err) => {
        const detail = err?.error?.detail;
        if (
          action === 'login'
          && err?.status === 404
          && detail?.code === 'social_account_not_found'
        ) {
          this.pendingSocialRegistration = { provider, credential };
          this.socialRegisterForm.reset({ role: 'PATIENT' });
          this.mode = 'social-register';
          this.errorMessage = '';
          this.infoMessage = '';
          this.isSubmitting = false;
          this.socialProviderInProgress = null;
          return;
        }
        this.errorMessage = this.getErrorMessage(err, 'ERRORS.AUTH_SOCIAL_FAILED');
        this.isSubmitting = false;
        this.socialProviderInProgress = null;
      },
      complete: () => {
        this.isSubmitting = false;
        this.socialProviderInProgress = null;
      },
    });
  }

  private handleSocialAuthSuccess(user: User, isNewUser: boolean): void {
    const isDoctorUser = user.role === 'DOCTOR' || user.is_doctor === true;
    if (isNewUser && !isDoctorUser) {
      sessionStorage.setItem(AuthPageComponent.TRIAL_WELCOME_KEY, 'true');
    }
    this.pendingSocialRegistration = null;
    this.redirectAfterAuth(user);
  }

  private redirectAfterAuth(user: User): void {
    if (user.role === 'ADMIN') {
      void this.router.navigateByUrl('/admin');
      return;
    }
    const isDoctor = user.role === 'DOCTOR' || user.is_doctor === true;
    const target = isDoctor ? '/doctor' : '/patient';
    void this.router.navigateByUrl(target);
  }
}
