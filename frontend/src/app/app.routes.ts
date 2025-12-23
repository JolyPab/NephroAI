import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'auth' },
  {
    path: 'auth',
    data: { hideToolbar: true, title: 'Sign in / Sign up' },
    loadChildren: () => import('./features/auth/auth.module').then((m) => m.AuthModule),
  },
  {
    path: 'patient',
    canActivate: [authGuard],
    data: { roles: ['PATIENT'], tabbar: true, tabbarBase: '/patient' },
    loadChildren: () => import('./features/patient/patient.module').then((m) => m.PatientModule),
  },
  {
    path: 'doctor',
    // Temporarily allow doctor module without role guard to avoid navigation loop
    data: { accent: 'doctor' },
    loadChildren: () => import('./features/doctor/doctor.module').then((m) => m.DoctorModule),
  },
  { path: '**', redirectTo: 'auth' },
];
