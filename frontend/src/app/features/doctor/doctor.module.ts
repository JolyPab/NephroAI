import { NgModule } from '@angular/core';

import { SharedModule } from '../../shared/shared.module';
import { DoctorRoutingModule } from './doctor-routing.module';
import { DoctorPatientsPageComponent } from './pages/patients/doctor-patients-page.component';
import { DoctorPatientDetailPageComponent } from './pages/patient-detail/doctor-patient-detail-page.component';
import { DoctorPatientChatPageComponent } from './pages/patient-chat/doctor-patient-chat-page.component';

@NgModule({
  declarations: [DoctorPatientsPageComponent, DoctorPatientDetailPageComponent, DoctorPatientChatPageComponent],
  imports: [SharedModule, DoctorRoutingModule],
})
export class DoctorModule {}

