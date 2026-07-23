import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { AdminDashboardPageComponent } from './pages/dashboard/admin-dashboard-page.component';

const routes: Routes = [
  {
    path: '',
    component: AdminDashboardPageComponent,
    data: { hideToolbar: true },
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AdminRoutingModule {}
