import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { DoctorService } from '../../../../core/services/doctor.service';
import { DoctorPatientSummary } from '../../../../core/models/doctor.model';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-doctor-patients-page',
  standalone: false,
  templateUrl: './doctor-patients-page.component.html',
  styleUrls: ['./doctor-patients-page.component.scss'],
})
export class DoctorPatientsPageComponent implements OnInit {
  private readonly doctorService = inject(DoctorService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  readonly user = this.auth.user;

  loading = true;
  patients: DoctorPatientSummary[] = [];
  errorMessage = '';
  savingName = false;
  nameMessage = '';
  nameError = '';

  readonly nameForm = this.fb.nonNullable.group({
    full_name: [this.user()?.full_name ?? '', [Validators.required, Validators.minLength(2)]],
  });

  ngOnInit(): void {
    this.doctorService.listPatients().subscribe({
      next: (response) => {
        this.patients = response?.patients ?? [];
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'Failed to load patients list.';
        this.loading = false;
      },
    });
  }

  openPatient(patient: DoctorPatientSummary): void {
    void this.router.navigate(['/doctor/patient', patient.patient_id]);
  }

  saveName(): void {
    if (this.nameForm.invalid) {
      this.nameForm.markAllAsTouched();
      return;
    }
    this.savingName = true;
    this.nameMessage = '';
    this.nameError = '';
    const { full_name } = this.nameForm.getRawValue();
    this.auth.updateProfile({ full_name }).subscribe({
      next: () => {
        this.savingName = false;
        this.nameMessage = 'doctor.nameSaved';
      },
      error: (err) => {
        this.nameError = err?.error?.detail ?? 'Failed to update name.';
        this.savingName = false;
      },
    });
  }
}
