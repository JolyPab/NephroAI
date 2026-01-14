import { CommonModule } from '@angular/common';
import { Component, DestroyRef, computed, inject } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs/operators';
import { TranslateModule } from '@ngx-translate/core';

import { AuthService } from './core/services/auth.service';
import { LanguageService } from './core/services/language.service';
import { ThemeService } from './core/services/theme.service';
import { GlassToolbarComponent } from './shared/components/glass-toolbar/glass-toolbar.component';
import { GlassTabbarComponent } from './shared/components/glass-tabbar/glass-tabbar.component';
import { GlassButtonDirective } from './shared/components/glass-button/glass-button.directive';

type ToolbarAccent = 'default' | 'doctor';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, GlassToolbarComponent, GlassTabbarComponent, GlassButtonDirective, TranslateModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class AppComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly themeService = inject(ThemeService);
  private readonly languageService = inject(LanguageService);

  readonly user = this.auth.user;
  readonly isAuthenticated = this.auth.isAuthenticated;
  readonly userEmail = computed(() => this.user()?.email ?? '');

  toolbarTitle = 'COMMON.APP_NAME';
  toolbarSubtitle = '';
  toolbarAccent: ToolbarAccent = 'default';
  showToolbar = true;
  showTabbar = false;
  showBack = false;
  tabbarBase = '/patient';
  private backLink?: string;

  constructor() {
    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => this.updateShell());

    this.updateShell();
  }

  ngOnInit(): void {
    this.languageService.init();
    // Restore authenticated user on page reload so toolbar/logout stay in sync
    this.auth.loadProfile().subscribe();
  }

  logout(): void {
    this.auth.logout().subscribe({
      complete: () => this.router.navigate(['/auth']),
      error: () => this.router.navigate(['/auth']),
    });
  }

  handleBack(): void {
    if (this.backLink) {
      void this.router.navigateByUrl(this.backLink);
    } else {
      window.history.back();
    }
  }

  private updateShell(): void {
    const data = this.collectRouteData();

    this.toolbarTitle = (data['title'] as string) ?? 'COMMON.APP_NAME';
    this.toolbarSubtitle = (data['subtitle'] as string) ?? '';
    this.toolbarAccent = (data['accent'] as ToolbarAccent) ?? 'default';
    this.showToolbar = data['hideToolbar'] !== true;
    this.showTabbar = data['tabbar'] === true;
    this.tabbarBase = (data['tabbarBase'] as string) ?? '/patient';
    this.showBack = data['showBack'] === true;
    this.backLink = data['back'] as string | undefined;
  }

  private collectRouteData(): Record<string, unknown> {
    const aggregate: Record<string, unknown> = {};
    let route: ActivatedRoute | null = this.activatedRoute;

    while (route) {
      Object.assign(aggregate, route.snapshot?.data ?? {});
      route = route.firstChild ?? null;
    }

    return aggregate;
  }

}
