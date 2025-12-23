import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';

import { ApiService } from './services/api.service';
import { AuthService } from './services/auth.service';
import { TokenService } from './services/token.service';
import { PatientService } from './services/patient.service';
import { DoctorService } from './services/doctor.service';
import { AdviceClientService } from './services/advice.service';

@NgModule({
  imports: [
    CommonModule,
    HttpClientModule,
    NgbModule,
    TranslateModule.forRoot({
      loader: {
        provide: TranslateLoader,
        useFactory: HttpLoaderFactory,
        deps: [HttpClient],
      },
      defaultLanguage: 'en',
    }),
  ],
  exports: [NgbModule, TranslateModule],
  providers: [ApiService, AuthService, TokenService, PatientService, DoctorService, AdviceClientService],
})
export class CoreModule {}

export function HttpLoaderFactory(http: HttpClient) {
  const loader: TranslateLoader = {
    getTranslation: (lang: string) =>
      http.get<Record<string, string>>(`assets/i18n/${lang}.json`) as any,
  };
  return loader;
}

