import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../../core/services/auth.service';
import { User } from '../../../../core/models/user.model';

@Component({
  selector: 'app-auth-page',
  standalone: false,
  templateUrl: './auth-page.component.html',
  styleUrls: ['./auth-page.component.scss'],
})
export class AuthPageComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  mode: 'login' | 'register' = 'login';
  isSubmitting = false;
  errorMessage = '';

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

  ngOnInit(): void {
    this.auth.loadProfile().subscribe((user) => {
      if (user) {
        this.redirectAfterAuth(user);
      }
    });
  }

  toggleMode(): void {
    this.mode = this.mode === 'login' ? 'register' : 'login';
    this.errorMessage = '';
  }

  submitLogin(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    this.auth.login(this.loginForm.getRawValue()).subscribe({
      next: (user) => this.redirectAfterAuth(user),
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'Unable to sign in. Check your email and password.';
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  submitRegister(): void {
    if (this.registerForm.invalid || this.registerForm.value.password !== this.registerForm.value.confirmPassword) {
      this.registerForm.markAllAsTouched();
      if (this.registerForm.value.password !== this.registerForm.value.confirmPassword) {
        this.errorMessage = 'Passwords must match.';
      }
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';
    const { email, password, role, full_name } = this.registerForm.getRawValue();
    this.auth.register({ email, password, role, full_name }).subscribe({
      next: (user) => this.redirectAfterAuth(user),
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'Registration failed. Please try again.';
        this.isSubmitting = false;
      },
      complete: () => (this.isSubmitting = false),
    });
  }

  private redirectAfterAuth(user: User): void {
    const isDoctor = user.role === 'DOCTOR' || user.is_doctor === true;
    const target = isDoctor ? '/doctor' : '/patient';
    void this.router.navigateByUrl(target);
  }
}
