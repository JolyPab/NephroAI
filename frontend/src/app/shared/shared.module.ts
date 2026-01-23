import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { TranslateModule } from '@ngx-translate/core';
import { NgChartsModule } from 'ng2-charts';

import { PatientTabBarComponent } from './components/patient-tab-bar/patient-tab-bar.component';
import { GlassCardComponent } from './components/glass-card/glass-card.component';
import { GlassButtonDirective } from './components/glass-button/glass-button.directive';
import { GlassInputComponent } from './components/glass-input/glass-input.component';
import { GlassToolbarComponent } from './components/glass-toolbar/glass-toolbar.component';
import { GlassTabbarComponent } from './components/glass-tabbar/glass-tabbar.component';
import { LatestReportSummaryComponent } from './components/latest-report-summary/latest-report-summary.component';
import { ChatShellComponent } from './components/chat-shell/chat-shell.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    NgbModule,
    TranslateModule,
    NgChartsModule,
    PatientTabBarComponent,
    GlassCardComponent,
    GlassButtonDirective,
    GlassInputComponent,
    GlassToolbarComponent,
    GlassTabbarComponent,
    LatestReportSummaryComponent,
    ChatShellComponent,
  ],
  exports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    NgbModule,
    TranslateModule,
    NgChartsModule,
    PatientTabBarComponent,
    GlassCardComponent,
    GlassButtonDirective,
    GlassInputComponent,
    GlassToolbarComponent,
    GlassTabbarComponent,
    LatestReportSummaryComponent,
    ChatShellComponent,
  ],
})
export class SharedModule {}

