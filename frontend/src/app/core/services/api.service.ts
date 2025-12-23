import { HttpClient, HttpParams } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = environment.BASE_API;

  constructor(@Inject(HttpClient) private readonly http: HttpClient) {}

  get<T>(url: string, params?: Record<string, string | number | boolean | undefined>): Observable<T> {
    return this.http.get<T>(this.resolveUrl(url), {
      params: this.toHttpParams(params),
    });
  }

  post<T>(url: string, body: unknown, options?: { params?: Record<string, string | number | boolean | undefined> }): Observable<T> {
    return this.http.post<T>(this.resolveUrl(url), body, {
      params: this.toHttpParams(options?.params),
    });
  }

  patch<T>(url: string, body: unknown, options?: { params?: Record<string, string | number | boolean | undefined> }): Observable<T> {
    return this.http.patch<T>(this.resolveUrl(url), body, {
      params: this.toHttpParams(options?.params),
    });
  }

  put<T>(url: string, body: unknown): Observable<T> {
    return this.http.put<T>(this.resolveUrl(url), body);
  }

  delete<T>(url: string): Observable<T> {
    return this.http.delete<T>(this.resolveUrl(url));
  }

  postForm<T>(url: string, form: FormData): Observable<T> {
    return this.http.post<T>(this.resolveUrl(url), form);
  }

  resolveUrl(path: string): string {
    if (path.startsWith('http')) {
      return path;
    }
    if (!path.startsWith('/')) {
      path = `/${path}`;
    }
    return `${this.baseUrl}${path}`;
  }

  private toHttpParams(params?: Record<string, string | number | boolean | undefined>): HttpParams | undefined {
    if (!params) {
      return undefined;
    }
    let httpParams = new HttpParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        httpParams = httpParams.set(key, value.toString());
      }
    });
    return httpParams;
  }
}
