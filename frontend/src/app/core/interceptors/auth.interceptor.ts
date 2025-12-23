import { HttpEvent, HttpHandlerFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable } from 'rxjs';

import { TokenService } from '../services/token.service';
import { environment } from '../../../environments/environment';

export function authInterceptor(req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> {
  const tokenService = inject(TokenService);

  const token = tokenService.accessToken;

  // In dev/prod we send only Bearer token (no cookies/withCredentials) to avoid CORS issues.
  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  return next(req);
}
