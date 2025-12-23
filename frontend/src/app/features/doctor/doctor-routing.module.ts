import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { DoctorPatientsPageComponent } from './pages/patients/doctor-patients-page.component';
import { DoctorPatientDetailPageComponent } from './pages/patient-detail/doctor-patient-detail-page.component';

const routes: Routes = [
  {
    path: '',
    component: DoctorPatientsPageComponent,
    data: {
      title: 'Doctor workspace',
      subtitle: 'Patients who shared their labs with you',
      accent: 'doctor',
    },
  },
  {
    path: 'patient/:id',
    component: DoctorPatientDetailPageComponent,
    data: {
      title: 'Patient card',
      subtitle: 'Charts and metrics for the selected period',
      accent: 'doctor',
      showBack: true,
      back: '/doctor',
    },
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class DoctorRoutingModule {}
