import { NgModule } from '@angular/core';

import { SharedModule } from '../../shared/shared.module';
import { V2RoutingModule } from './v2-routing.module';
import { V2DashboardPageComponent } from './pages/dashboard/v2-dashboard-page.component';
import { V2SeriesPageComponent } from './pages/series/v2-series-page.component';

@NgModule({
  declarations: [V2DashboardPageComponent],
  imports: [SharedModule, V2RoutingModule, V2SeriesPageComponent],
})
export class V2Module {}
