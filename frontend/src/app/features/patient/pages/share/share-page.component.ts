import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';

import { PatientService } from '../../../../core/services/patient.service';
import { ShareGrant } from '../../../../core/models/share.model';

@Component({
  selector: 'app-patient-share-page',
  standalone: false,
  templateUrl: './share-page.component.html',
  styleUrls: ['./share-page.component.scss'],
})
export class PatientSharePageComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly patientService = inject(PatientService);

  isSubmitting = false;
  toastMessage = '';
  toastTone: 'success' | 'danger' | 'info' = 'info';
  grants: ShareGrant[] = [];

  readonly shareForm = this.fb.nonNullable.group({
    doctor_email: ['', [Validators.required, Validators.email]],
  });

  ngOnInit(): void {
    this.refreshGrants();
  }

  submit(): void {
    if (this.shareForm.invalid) {
      this.shareForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    const { doctor_email } = this.shareForm.getRawValue();
    this.patientService.shareWithDoctor(doctor_email).subscribe({
      next: (grant) => {
        this.toastTone = 'success';
        this.toastMessage = 'Access granted.';
        this.isSubmitting = false;
        this.shareForm.reset({ doctor_email: '' });
        this.grants = [grant, ...this.grants.filter((item) => item.doctor_email !== grant.doctor_email)];
      },
      error: (err) => {
        this.toastTone = 'danger';
        this.toastMessage = err?.error?.detail ?? 'Failed to grant access.';
        this.isSubmitting = false;
      },
    });
  }

  private refreshGrants(): void {
    this.patientService.getAccessGrants().subscribe((grants) => {
      this.grants = grants ?? [];
      if (!this.grants.length) {
        this.toastTone = 'info';
        this.toastMessage = 'No granted accesses yet. Invite a doctor by email.';
      }
    });
  }
}
