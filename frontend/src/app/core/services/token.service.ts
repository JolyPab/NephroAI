import { Injectable } from '@angular/core';

const ACCESS_TOKEN_KEY = 'medic.accessToken';
const REFRESH_TOKEN_KEY = 'medic.refreshToken';

@Injectable({ providedIn: 'root' })
export class TokenService {
  get accessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  set accessToken(token: string | null) {
    if (token) {
      localStorage.setItem(ACCESS_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
    }
  }

  get refreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  set refreshToken(token: string | null) {
    if (token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  }

  clear(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}
