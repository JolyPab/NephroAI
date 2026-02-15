import { NgModule } from '@angular/core';

import { SharedModule } from '../../shared/shared.module';
import { DoctorRoutingModule } from './doctor-routing.module';
import { DoctorPatientsPageComponent } from './pages/patients/doctor-patients-page.component';
import { DoctorPatientDetailPageComponent } from './pages/patient-detail/doctor-patient-detail-page.component';
import { DoctorPatientChatPageComponent } from './pages/patient-chat/doctor-patient-chat-page.component';
import { V2SeriesPageComponent } from '../v2/pages/series/v2-series-page.component';
import { V2MetricSelectorComponent } from '../v2/components/metric-selector/v2-metric-selector.component';

@NgModule({
  declarations: [DoctorPatientsPageComponent, DoctorPatientDetailPageComponent, DoctorPatientChatPageComponent],
  imports: [SharedModule, DoctorRoutingModule, V2SeriesPageComponent, V2MetricSelectorComponent],
})
export class DoctorModule {}

