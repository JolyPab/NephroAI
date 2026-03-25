import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-patient-shell',
  standalone: false,
  templateUrl: './patient-shell.component.html',
  styleUrls: ['./patient-shell.component.scss'],
})
export class PatientShellComponent {
  private router = inject(Router);

  get isChat(): boolean {
    return this.router.url.includes('/chat');
  }
}
