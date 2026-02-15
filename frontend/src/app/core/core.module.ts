import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { TranslateModule } from '@ngx-translate/core';

import { ApiService } from './services/api.service';
import { AuthService } from './services/auth.service';
import { TokenService } from './services/token.service';
import { PatientService } from './services/patient.service';
import { DoctorService } from './services/doctor.service';
import { AdviceClientService } from './services/advice.service';
import { V2Service } from './services/v2.service';

@NgModule({
  imports: [
    CommonModule,
    HttpClientModule,
    NgbModule,
    TranslateModule,
  ],
  exports: [NgbModule, TranslateModule],
  providers: [ApiService, AuthService, TokenService, PatientService, DoctorService, AdviceClientService, V2Service],
})
export class CoreModule {}

