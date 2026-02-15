import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';
import { AdviceResponseModel } from '../models/advice.model';

@Injectable({ providedIn: 'root' })
export class AdviceClientService {
  private readonly api = inject(ApiService);

  ask(
    question: string,
    metricNames?: string[],
    days?: number,
    language?: 'es' | 'en',
  ): Observable<AdviceResponseModel> {
    return this.api.post<AdviceResponseModel>('/advice', {
      question,
      metricNames,
      days,
      language,
    });
  }
}
