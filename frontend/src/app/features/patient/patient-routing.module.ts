import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { PatientShellComponent } from './components/patient-shell/patient-shell.component';
import { PatientDashboardPageComponent } from './pages/dashboard/dashboard-page.component';
import { PatientUploadPageComponent } from './pages/upload/upload-page.component';
import { PatientChartsPageComponent } from './pages/charts/charts-page.component';
import { PatientSharePageComponent } from './pages/share/share-page.component';
import { PatientChatPageComponent } from './pages/chat/chat-page.component';
import { PatientProfilePageComponent } from './pages/profile/profile-page.component';
import { PatientConsultationsPageComponent } from './pages/consultations/consultations-page.component';

const routes: Routes = [
  {
    path: '',
    component: PatientShellComponent,
    data: {
      title: 'PATIENT.WORKSPACE.TITLE',
      subtitle: 'PATIENT.WORKSPACE.SUBTITLE',
      tabbar: true,
    },
    children: [
      {
        path: '',
        component: PatientDashboardPageComponent,
        data: {
          title: 'PATIENT.DASHBOARD.TITLE',
          subtitle: 'PATIENT.DASHBOARD.SUBTITLE',
          tabbar: true,
        },
      },
      {
        path: 'upload',
        component: PatientUploadPageComponent,
        data: {
          title: 'UPLOAD.TITLE',
          subtitle: 'UPLOAD.SUBTITLE',
          tabbar: true,
        },
      },
      {
        path: 'charts',
        component: PatientChartsPageComponent,
        data: {
          title: 'CHARTS.TITLE',
          subtitle: 'CHARTS.SUBTITLE',
          tabbar: true,
        },
      },
      {
        path: 'share',
        component: PatientSharePageComponent,
        data: {
          title: 'PATIENT.SHARE.TITLE',
          subtitle: 'PATIENT.SHARE.SUBTITLE',
          tabbar: true,
        },
      },
      {
        path: 'chat',
        component: PatientChatPageComponent,
        data: {
          title: 'PATIENT.CHAT.TITLE',
          subtitle: 'PATIENT.CHAT.SUBTITLE',
          tabbar: true,
        },
      },
      {
        path: 'consultations',
        component: PatientConsultationsPageComponent,
        data: {
          title: 'PATIENT.CONSULTATIONS.TITLE',
          subtitle: 'PATIENT.CONSULTATIONS.SUBTITLE',
          tabbar: true,
        },
      },
      {
        path: 'profile',
        component: PatientProfilePageComponent,
        data: {
          title: 'PATIENT.PROFILE.TITLE',
          subtitle: 'PATIENT.PROFILE.SUBTITLE',
          tabbar: false,
          showBack: true,
          back: '/patient',
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
