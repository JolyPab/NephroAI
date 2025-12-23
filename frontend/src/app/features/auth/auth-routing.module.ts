import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { AuthPageComponent } from './pages/auth-page/auth-page.component';

const routes: Routes = [
  {
    path: '',
    component: AuthPageComponent,
    data: {
      title: 'Sign in or sign up',
      subtitle: 'Secure access to your lab data',
      hideToolbar: true,
    },
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AuthRoutingModule {}
