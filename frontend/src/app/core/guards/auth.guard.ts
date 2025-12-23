import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map, of, switchMap } from 'rxjs';

import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/user.model';

export const authGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const allowedRoles = route.data?.['roles'] as UserRole[] | undefined;

  return auth.loadProfile().pipe(
    switchMap((user) => {
      if (!user) {
        void router.navigate(['/auth']);
        return of(false);
      }
      const role = user.role ?? (user.is_doctor ? 'DOCTOR' : 'PATIENT');
      if (allowedRoles && allowedRoles.length && !allowedRoles.includes(role)) {
        void router.navigate(['/auth']);
        return of(false);
      }
      return of(true);
    }),
  );
};
