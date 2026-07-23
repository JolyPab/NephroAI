import { NgModule } from '@angular/core';

import { SharedModule } from '../../shared/shared.module';
import { AdminRoutingModule } from './admin-routing.module';
import { AdminDashboardPageComponent } from './pages/dashboard/admin-dashboard-page.component';

@NgModule({
  declarations: [AdminDashboardPageComponent],
  imports: [SharedModule, AdminRoutingModule],
})
export class AdminModule {}
