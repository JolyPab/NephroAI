import { Component, Input } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';

interface TabItem {
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-patient-tab-bar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './patient-tab-bar.component.html',
  styleUrls: ['./patient-tab-bar.component.scss'],
})
export class PatientTabBarComponent {
  @Input() baseRoute = '/patient';

  readonly tabs: TabItem[] = [
    { label: 'Домой', icon: 'bi-house-heart', route: '' },
    { label: 'Загрузка', icon: 'bi-cloud-arrow-up', route: 'upload' },
    { label: 'Графики', icon: 'bi-graph-up', route: 'charts' },
    { label: 'Чат', icon: 'bi-chat-dots', route: 'chat' },
    { label: 'Профиль', icon: 'bi-person', route: 'profile' },
  ];
}
