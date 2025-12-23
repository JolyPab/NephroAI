import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { PatientShellComponent } from './components/patient-shell/patient-shell.component';
import { PatientDashboardPageComponent } from './pages/dashboard/dashboard-page.component';
import { PatientUploadPageComponent } from './pages/upload/upload-page.component';
import { PatientChartsPageComponent } from './pages/charts/charts-page.component';
import { PatientSharePageComponent } from './pages/share/share-page.component';
import { PatientChatPageComponent } from './pages/chat/chat-page.component';
import { PatientProfilePageComponent } from './pages/profile/profile-page.component';

const routes: Routes = [
  {
    path: '',
    component: PatientShellComponent,
    data: {
      title: 'Patient workspace',
      subtitle: 'All analyses, charts, and sharing in one place',
      tabbar: true,
    },
    children: [
      {
        path: '',
        component: PatientDashboardPageComponent,
        data: {
          title: 'Home',
          subtitle: 'Recent analyses and key trends',
          tabbar: true,
        },
      },
      {
        path: 'upload',
        component: PatientUploadPageComponent,
        data: {
          title: 'Upload analyses',
          subtitle: 'PDF → OCR → structured data',
          tabbar: true,
        },
      },
      {
        path: 'charts',
        component: PatientChartsPageComponent,
        data: {
          title: 'Charts',
          subtitle: 'Compare with normal ranges and trends over time',
          tabbar: true,
        },
      },
      {
        path: 'share',
        component: PatientSharePageComponent,
        data: {
          title: 'Doctor access',
          subtitle: 'Manage granting and revoking permissions',
          tabbar: true,
        },
      },
      {
        path: 'chat',
        component: PatientChatPageComponent,
        data: {
          title: 'AI advice',
          subtitle: 'Ask about your labs with safe hints',
          tabbar: true,
        },
      },
      {
        path: 'profile',
        component: PatientProfilePageComponent,
        data: {
          title: 'Profile',
          subtitle: 'Account and theme settings',
          tabbar: true,
        },
      },
    ],
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class PatientRoutingModule {}
