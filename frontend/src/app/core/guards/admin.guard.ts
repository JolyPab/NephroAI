import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AdminService } from '../services/admin.service';

export const adminGuard: CanActivateFn = () => {
  const admin = inject(AdminService);
  const router = inject(Router);

  return admin.access().pipe(
    map(() => true),
    catchError((error) => {
      void router.navigateByUrl(error?.status === 401 ? '/auth' : '/patient');
      return of(false);
    }),
  );
};
