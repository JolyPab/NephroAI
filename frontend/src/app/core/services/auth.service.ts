import { Injectable, computed, inject, signal } from '@angular/core';
import { catchError, map, tap } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

import { ApiService } from './api.service';
import { TokenService } from './token.service';
import { User } from '../models/user.model';

export interface AuthResponse {
  user: User;
  accessToken?: string;
  refreshToken?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly tokens = inject(TokenService);

  private readonly userSignal = signal<User | null>(null);
  readonly user = computed(() => this.userSignal());
  readonly isAuthenticated = computed(() => !!this.userSignal());

  login(credentials: { email: string; password: string }): Observable<User> {
    return this.api.post<AuthResponse>('/auth/login', credentials).pipe(
      tap((response) => {
        console.log('[DEBUG] Login response:', response);
        this.handleAuthSuccess(response);
        this.userSignal.set(this.normalizeUser(response.user));
      }),
      map((response) => this.normalizeUser(response.user)),
    );
  }

  register(payload: { email: string; password: string; role?: string; full_name?: string }): Observable<User> {
    const body: any = {
      email: payload.email,
      password: payload.password,
      is_doctor: payload.role === 'DOCTOR',
      full_name: payload.full_name,
    };
    return this.api.post<AuthResponse>('/auth/register', body).pipe(
      tap((response) => {
        console.log('[DEBUG] Register response:', response);
        this.handleAuthSuccess(response);
        this.userSignal.set(this.normalizeUser(response.user));
      }),
      map((response) => this.normalizeUser(response.user)),
    );
  }

  logout(): Observable<void> {
    this.tokens.clear();
    this.userSignal.set(null);
    return this.api.post('/auth/logout', {}).pipe(map(() => undefined));
  }

  loadProfile(): Observable<User | null> {
    if (this.userSignal()) {
      return of(this.userSignal());
    }
    return this.api.get<User>('/me').pipe(
      map((user) => this.normalizeUser(user)),
      tap((user) => this.userSignal.set(user)),
      catchError(() => {
        this.userSignal.set(null);
        return of(null);
      }),
    );
  }

  private handleAuthSuccess(response: AuthResponse): void {
    console.log('[DEBUG] handleAuthSuccess:', response);
    if (response.accessToken) {
      console.log('[DEBUG] Saving accessToken to localStorage');
      this.tokens.accessToken = response.accessToken;
      console.log('[DEBUG] Token saved, now in localStorage:', this.tokens.accessToken ? 'YES' : 'NO');
    } else {
      console.warn('[DEBUG] No accessToken in response!');
    }
    if (response.refreshToken) {
      this.tokens.refreshToken = response.refreshToken;
    }
  }

  private normalizeUser(user: User): User {
    const role = user.role ?? (user.is_doctor ? 'DOCTOR' : 'PATIENT');
    return { ...user, role };
  }

  updateProfile(payload: { full_name: string }): Observable<User> {
    return this.api.patch<User>('/me', payload).pipe(
      map((user) => this.normalizeUser(user)),
      tap((user) => this.userSignal.set(user)),
    );
  }
}
