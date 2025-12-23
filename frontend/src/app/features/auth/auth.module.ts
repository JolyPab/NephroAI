import { NgModule } from '@angular/core';

import { SharedModule } from '../../shared/shared.module';
import { AuthRoutingModule } from './auth-routing.module';
import { AuthPageComponent } from './pages/auth-page/auth-page.component';

@NgModule({
  declarations: [AuthPageComponent],
  imports: [SharedModule, AuthRoutingModule],
})
export class AuthModule {}

