import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { V2DashboardPageComponent } from './pages/dashboard/v2-dashboard-page.component';
import { V2SeriesPageComponent } from './pages/series/v2-series-page.component';

const routes: Routes = [
  {
    path: '',
    component: V2DashboardPageComponent,
    data: {
      title: 'V2 Dashboard',
      subtitle: 'Upload report and inspect analytes',
    },
  },
  {
    path: 'analyte/:analyteKey',
    component: V2SeriesPageComponent,
    data: {
      title: 'V2 Series',
      subtitle: 'Analyte trend and evidence',
      showBack: true,
      back: '/v2',
    },
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class V2RoutingModule {}
