import { NgModule } from '@angular/core';

import { SharedModule } from '../../shared/shared.module';
import { PatientRoutingModule } from './patient-routing.module';
import { PatientShellComponent } from './components/patient-shell/patient-shell.component';
import { PatientDashboardPageComponent } from './pages/dashboard/dashboard-page.component';
import { PatientUploadPageComponent } from './pages/upload/upload-page.component';
import { PatientChartsPageComponent } from './pages/charts/charts-page.component';
import { PatientSharePageComponent } from './pages/share/share-page.component';
import { PatientChatPageComponent } from './pages/chat/chat-page.component';
import { PatientProfilePageComponent } from './pages/profile/profile-page.component';

@NgModule({
  declarations: [
    PatientShellComponent,
    PatientDashboardPageComponent,
    PatientUploadPageComponent,
    PatientChartsPageComponent,
    PatientSharePageComponent,
    PatientChatPageComponent,
    PatientProfilePageComponent,
  ],
  imports: [SharedModule, PatientRoutingModule],
})
export class PatientModule {}

