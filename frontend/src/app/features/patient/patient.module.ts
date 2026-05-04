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
import { PatientConsultationsPageComponent } from './pages/consultations/consultations-page.component';
import { V2SeriesPageComponent } from '../v2/pages/series/v2-series-page.component';
import { V2MetricSelectorComponent } from '../v2/components/metric-selector/v2-metric-selector.component';
import { ChatSidebarComponent } from './components/chat-sidebar/chat-sidebar.component';
import { ChatMemoryPanelComponent } from './components/chat-memory-panel/chat-memory-panel.component';

@NgModule({
  declarations: [
    PatientShellComponent,
    PatientDashboardPageComponent,
    PatientUploadPageComponent,
    PatientChartsPageComponent,
    PatientSharePageComponent,
    PatientChatPageComponent,
    PatientConsultationsPageComponent,
    PatientProfilePageComponent,
  ],
  imports: [SharedModule, PatientRoutingModule, V2SeriesPageComponent, V2MetricSelectorComponent,
            ChatSidebarComponent, ChatMemoryPanelComponent],
})
export class PatientModule {}

