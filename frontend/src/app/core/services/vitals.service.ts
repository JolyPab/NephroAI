import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';

export interface BloodPressureCreate {
  systolic: number;
  diastolic: number;
  pulse?: number | null;
  measured_at?: string | null;
  notes?: string | null;
}

export interface BloodPressureItem {
  id: number;
  measured_at: string;
  systolic: number;
  diastolic: number;
  pulse: number | null;
  notes: string | null;
  created_at: string;
}

export interface TemperatureCreate {
  value: number;
  measured_at?: string | null;
  notes?: string | null;
}

export interface TemperatureItem {
  id: number;
  measured_at: string;
  value: number;
  notes: string | null;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class VitalsService {
  private readonly api = inject(ApiService);

  createBloodPressure(payload: BloodPressureCreate): Observable<BloodPressureItem> {
    return this.api.post<BloodPressureItem>('/vitals/blood-pressure', payload);
  }

  listBloodPressure(): Observable<BloodPressureItem[]> {
    return this.api.get<BloodPressureItem[]>('/vitals/blood-pressure');
  }

  createTemperature(payload: TemperatureCreate): Observable<TemperatureItem> {
    return this.api.post<TemperatureItem>('/vitals/temperature', payload);
  }

  listTemperature(): Observable<TemperatureItem[]> {
    return this.api.get<TemperatureItem[]>('/vitals/temperature');
  }
}
