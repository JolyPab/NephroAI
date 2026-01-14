import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';

interface TabItem {
  label: string;
  icon: string;
  route: string;
  exact?: boolean;
}

@Component({
  selector: 'app-glass-tabbar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, TranslateModule],
  templateUrl: './glass-tabbar.component.html',
  styleUrls: ['./glass-tabbar.component.scss'],
})
export class GlassTabbarComponent {
  @Input() baseRoute = '/patient';

  readonly items: TabItem[] = [
    { label: 'COMMON.NAV.HOME', icon: 'home', route: '', exact: true },
    { label: 'COMMON.NAV.UPLOAD', icon: 'upload', route: 'upload' },
    { label: 'COMMON.NAV.CHARTS', icon: 'monitoring', route: 'charts' },
    { label: 'COMMON.NAV.CHAT', icon: 'forum', route: 'chat' },
    { label: 'COMMON.NAV.PROFILE', icon: 'person', route: 'profile' },
  ];

  fullRoute(item: TabItem): string {
    const cleanedBase = this.baseRoute.endsWith('/') ? this.baseRoute.slice(0, -1) : this.baseRoute;
    if (!item.route) {
      return cleanedBase || '/patient';
    }
    return `${cleanedBase}/${item.route}`;
  }

  trackByLabel(_: number, item: TabItem): string {
    return item.label;
  }
}
