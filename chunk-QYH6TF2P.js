import { injectQuery as __vite__injectQuery } from "/@vite/client";import { createHotContext as __vite__createHotContext } from "/@vite/client";import.meta.hot = __vite__createHotContext("/chunk-QYH6TF2P.js");import {
  AuthService
} from "/chunk-UO5WSPBZ.js";
import {
  GlassCardComponent,
  GlassInputComponent,
  PatientTabBarComponent,
  SharedModule,
  glass_card_component_exports,
  glass_input_component_exports,
  patient_tab_bar_component_exports
} from "/chunk-PY2NVEHP.js";
import {
  GlassButtonDirective,
  GlassTabbarComponent,
  GlassToolbarComponent,
  glass_button_directive_exports,
  glass_tabbar_component_exports,
  glass_toolbar_component_exports
} from "/chunk-BM63WUAP.js";

// src/app/features/auth/auth.module.ts
import { NgModule as NgModule2 } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";

// src/app/features/auth/auth-routing.module.ts
import { NgModule } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import { RouterModule } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";

// src/app/features/auth/pages/auth-page/auth-page.component.ts
import { Component, inject } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import { FormBuilder, Validators } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_forms.js?v=24701eb5";
import { Router } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
import * as i0 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import * as i1 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_common.js?v=24701eb5";
import * as i2 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_forms.js?v=24701eb5";
import * as i3 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
import * as i4 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@ng-bootstrap_ng-bootstrap.js?v=24701eb5";
import * as i5 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@ngx-translate_core.js?v=24701eb5";
import * as i6 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/ng2-charts.js?v=24701eb5";
function AuthPageComponent_form_15_div_5_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275elementStart(0, "div", 14)(1, "span", 6);
    i0.\u0275\u0275text(2, "error");
    i0.\u0275\u0275elementEnd();
    i0.\u0275\u0275elementStart(3, "span");
    i0.\u0275\u0275text(4);
    i0.\u0275\u0275elementEnd()();
  }
  if (rf & 2) {
    const ctx_r1 = i0.\u0275\u0275nextContext(2);
    i0.\u0275\u0275advance(4);
    i0.\u0275\u0275textInterpolate(ctx_r1.errorMessage);
  }
}
function AuthPageComponent_form_15_span_7_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275element(0, "span", 15);
  }
}
function AuthPageComponent_form_15_Template(rf, ctx) {
  if (rf & 1) {
    const _r1 = i0.\u0275\u0275getCurrentView();
    i0.\u0275\u0275elementStart(0, "form", 8);
    i0.\u0275\u0275listener("ngSubmit", function AuthPageComponent_form_15_Template_form_ngSubmit_0_listener() {
      i0.\u0275\u0275restoreView(_r1);
      const ctx_r1 = i0.\u0275\u0275nextContext();
      return i0.\u0275\u0275resetView(ctx_r1.submitLogin());
    });
    i0.\u0275\u0275element(1, "app-glass-input", 9);
    i0.\u0275\u0275pipe(2, "translate");
    i0.\u0275\u0275element(3, "app-glass-input", 10);
    i0.\u0275\u0275pipe(4, "translate");
    i0.\u0275\u0275template(5, AuthPageComponent_form_15_div_5_Template, 5, 1, "div", 11);
    i0.\u0275\u0275elementStart(6, "button", 12);
    i0.\u0275\u0275template(7, AuthPageComponent_form_15_span_7_Template, 1, 0, "span", 13);
    i0.\u0275\u0275elementStart(8, "span");
    i0.\u0275\u0275text(9);
    i0.\u0275\u0275pipe(10, "translate");
    i0.\u0275\u0275pipe(11, "translate");
    i0.\u0275\u0275elementEnd()()();
  }
  if (rf & 2) {
    const ctx_r1 = i0.\u0275\u0275nextContext();
    i0.\u0275\u0275property("formGroup", ctx_r1.loginForm);
    i0.\u0275\u0275advance();
    i0.\u0275\u0275property("label", i0.\u0275\u0275pipeBind1(2, 8, "auth.email"));
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275property("label", i0.\u0275\u0275pipeBind1(4, 10, "auth.password"));
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275property("ngIf", ctx_r1.errorMessage);
    i0.\u0275\u0275advance();
    i0.\u0275\u0275property("glassBlock", true)("disabled", ctx_r1.isSubmitting);
    i0.\u0275\u0275advance();
    i0.\u0275\u0275property("ngIf", ctx_r1.isSubmitting);
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275textInterpolate(ctx_r1.isSubmitting ? i0.\u0275\u0275pipeBind1(10, 12, "auth.signingIn") : i0.\u0275\u0275pipeBind1(11, 14, "auth.signInBtn"));
  }
}
function AuthPageComponent_form_16_div_18_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275elementStart(0, "div", 14)(1, "span", 6);
    i0.\u0275\u0275text(2, "error");
    i0.\u0275\u0275elementEnd();
    i0.\u0275\u0275elementStart(3, "span");
    i0.\u0275\u0275text(4);
    i0.\u0275\u0275elementEnd()();
  }
  if (rf & 2) {
    const ctx_r1 = i0.\u0275\u0275nextContext(2);
    i0.\u0275\u0275advance(4);
    i0.\u0275\u0275textInterpolate(ctx_r1.errorMessage);
  }
}
function AuthPageComponent_form_16_span_20_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275element(0, "span", 15);
  }
}
function AuthPageComponent_form_16_Template(rf, ctx) {
  if (rf & 1) {
    const _r3 = i0.\u0275\u0275getCurrentView();
    i0.\u0275\u0275elementStart(0, "form", 8);
    i0.\u0275\u0275listener("ngSubmit", function AuthPageComponent_form_16_Template_form_ngSubmit_0_listener() {
      i0.\u0275\u0275restoreView(_r3);
      const ctx_r1 = i0.\u0275\u0275nextContext();
      return i0.\u0275\u0275resetView(ctx_r1.submitRegister());
    });
    i0.\u0275\u0275element(1, "app-glass-input", 9);
    i0.\u0275\u0275pipe(2, "translate");
    i0.\u0275\u0275element(3, "app-glass-input", 16);
    i0.\u0275\u0275pipe(4, "translate");
    i0.\u0275\u0275element(5, "app-glass-input", 17);
    i0.\u0275\u0275pipe(6, "translate");
    i0.\u0275\u0275elementStart(7, "div", 18)(8, "label", 19);
    i0.\u0275\u0275text(9);
    i0.\u0275\u0275pipe(10, "translate");
    i0.\u0275\u0275elementEnd();
    i0.\u0275\u0275elementStart(11, "select", 20)(12, "option", 21);
    i0.\u0275\u0275text(13);
    i0.\u0275\u0275pipe(14, "translate");
    i0.\u0275\u0275elementEnd();
    i0.\u0275\u0275elementStart(15, "option", 22);
    i0.\u0275\u0275text(16);
    i0.\u0275\u0275pipe(17, "translate");
    i0.\u0275\u0275elementEnd()()();
    i0.\u0275\u0275template(18, AuthPageComponent_form_16_div_18_Template, 5, 1, "div", 11);
    i0.\u0275\u0275elementStart(19, "button", 12);
    i0.\u0275\u0275template(20, AuthPageComponent_form_16_span_20_Template, 1, 0, "span", 13);
    i0.\u0275\u0275elementStart(21, "span");
    i0.\u0275\u0275text(22);
    i0.\u0275\u0275pipe(23, "translate");
    i0.\u0275\u0275pipe(24, "translate");
    i0.\u0275\u0275elementEnd()()();
  }
  if (rf & 2) {
    const ctx_r1 = i0.\u0275\u0275nextContext();
    i0.\u0275\u0275property("formGroup", ctx_r1.registerForm);
    i0.\u0275\u0275advance();
    i0.\u0275\u0275property("label", i0.\u0275\u0275pipeBind1(2, 12, "auth.email"));
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275property("label", i0.\u0275\u0275pipeBind1(4, 14, "auth.password"));
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275property("label", i0.\u0275\u0275pipeBind1(6, 16, "auth.confirmPassword"));
    i0.\u0275\u0275advance(4);
    i0.\u0275\u0275textInterpolate(i0.\u0275\u0275pipeBind1(10, 18, "auth.role"));
    i0.\u0275\u0275advance(4);
    i0.\u0275\u0275textInterpolate(i0.\u0275\u0275pipeBind1(14, 20, "auth.patient"));
    i0.\u0275\u0275advance(3);
    i0.\u0275\u0275textInterpolate(i0.\u0275\u0275pipeBind1(17, 22, "auth.doctor"));
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275property("ngIf", ctx_r1.errorMessage);
    i0.\u0275\u0275advance();
    i0.\u0275\u0275property("glassBlock", true)("disabled", ctx_r1.isSubmitting);
    i0.\u0275\u0275advance();
    i0.\u0275\u0275property("ngIf", ctx_r1.isSubmitting);
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275textInterpolate(ctx_r1.isSubmitting ? i0.\u0275\u0275pipeBind1(23, 24, "auth.creating") : i0.\u0275\u0275pipeBind1(24, 26, "auth.createBtn"));
  }
}
var AuthPageComponent = class _AuthPageComponent {
  fb = inject(FormBuilder);
  auth = inject(AuthService);
  router = inject(Router);
  mode = "login";
  isSubmitting = false;
  errorMessage = "";
  loginForm = this.fb.nonNullable.group({
    email: ["", [Validators.required, Validators.email]],
    password: ["", [Validators.required, Validators.minLength(8)]]
  });
  registerForm = this.fb.nonNullable.group({
    email: ["", [Validators.required, Validators.email]],
    password: ["", [Validators.required, Validators.minLength(8)]],
    confirmPassword: ["", [Validators.required]],
    role: ["PATIENT"]
  });
  ngOnInit() {
    this.auth.loadProfile().subscribe((user) => {
      if (user) {
        this.redirectAfterAuth(user);
      }
    });
  }
  toggleMode() {
    this.mode = this.mode === "login" ? "register" : "login";
    this.errorMessage = "";
  }
  submitLogin() {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = "";
    this.auth.login(this.loginForm.getRawValue()).subscribe({
      next: (user) => this.redirectAfterAuth(user),
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? "Unable to sign in. Check your email and password.";
        this.isSubmitting = false;
      },
      complete: () => this.isSubmitting = false
    });
  }
  submitRegister() {
    if (this.registerForm.invalid || this.registerForm.value.password !== this.registerForm.value.confirmPassword) {
      this.registerForm.markAllAsTouched();
      if (this.registerForm.value.password !== this.registerForm.value.confirmPassword) {
        this.errorMessage = "Passwords must match.";
      }
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = "";
    const { email, password, role } = this.registerForm.getRawValue();
    this.auth.register({ email, password, role }).subscribe({
      next: (user) => this.redirectAfterAuth(user),
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? "Registration failed. Please try again.";
        this.isSubmitting = false;
      },
      complete: () => this.isSubmitting = false
    });
  }
  redirectAfterAuth(user) {
    const isDoctor = user.role === "DOCTOR" || user.is_doctor === true;
    const target = isDoctor ? "/doctor" : "/patient";
    void this.router.navigateByUrl(target);
  }
  static \u0275fac = function AuthPageComponent_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _AuthPageComponent)();
  };
  static \u0275cmp = /* @__PURE__ */ i0.\u0275\u0275defineComponent({ type: _AuthPageComponent, selectors: [["app-auth-page"]], standalone: false, decls: 17, vars: 10, consts: [[1, "auth-shell"], [3, "extraClass"], [1, "flex", "items-center", "justify-between"], [1, "text-2xl", "sm:text-3xl", "font-semibold", "text-[var(--text)]"], [1, "text-sm", "text-[var(--text-dim)]"], ["type", "button", "appGlassButton", "", 3, "click"], [1, "material-symbols-rounded"], ["class", "space-y-5", 3, "formGroup", "ngSubmit", 4, "ngIf"], [1, "space-y-5", 3, "ngSubmit", "formGroup"], ["placeholder", "you@example.com", "type", "email", "formControlName", "email", 3, "label"], ["placeholder", "Enter password", "type", "password", "formControlName", "password", 3, "label"], ["class", "toast-glass error", "role", "alert", 4, "ngIf"], ["type", "submit", "appGlassButton", "", 3, "glassBlock", "disabled"], ["class", "loader-dot", 4, "ngIf"], ["role", "alert", 1, "toast-glass", "error"], [1, "loader-dot"], ["placeholder", "Minimum 8 characters", "type", "password", "formControlName", "password", 3, "label"], ["placeholder", "Repeat the password", "type", "password", "formControlName", "confirmPassword", 3, "label"], [1, "flex", "flex-col", "gap-2"], [1, "text-xs", "uppercase", "tracking-[0.2em]", "text-[var(--text-dim)]"], ["formControlName", "role", 1, "input-glass"], ["value", "PATIENT"], ["value", "DOCTOR"]], template: function AuthPageComponent_Template(rf, ctx) {
    if (rf & 1) {
      i0.\u0275\u0275elementStart(0, "div", 0)(1, "app-glass-card", 1)(2, "div", 2)(3, "div")(4, "h1", 3);
      i0.\u0275\u0275text(5, "Medic Insight");
      i0.\u0275\u0275elementEnd();
      i0.\u0275\u0275elementStart(6, "p", 4);
      i0.\u0275\u0275text(7);
      i0.\u0275\u0275elementEnd()();
      i0.\u0275\u0275elementStart(8, "button", 5);
      i0.\u0275\u0275listener("click", function AuthPageComponent_Template_button_click_8_listener() {
        return ctx.toggleMode();
      });
      i0.\u0275\u0275elementStart(9, "span", 6);
      i0.\u0275\u0275text(10);
      i0.\u0275\u0275elementEnd();
      i0.\u0275\u0275elementStart(11, "span");
      i0.\u0275\u0275text(12);
      i0.\u0275\u0275pipe(13, "translate");
      i0.\u0275\u0275pipe(14, "translate");
      i0.\u0275\u0275elementEnd()()();
      i0.\u0275\u0275template(15, AuthPageComponent_form_15_Template, 12, 16, "form", 7)(16, AuthPageComponent_form_16_Template, 25, 28, "form", 7);
      i0.\u0275\u0275elementEnd()();
    }
    if (rf & 2) {
      i0.\u0275\u0275advance();
      i0.\u0275\u0275property("extraClass", "w-full max-w-xl glass-strong space-y-6");
      i0.\u0275\u0275advance(6);
      i0.\u0275\u0275textInterpolate1(" ", ctx.mode === "login" ? "Welcome back! Sign in to continue." : "Create an account to share your analyses and trends.", " ");
      i0.\u0275\u0275advance(3);
      i0.\u0275\u0275textInterpolate(ctx.mode === "login" ? "person_add" : "login");
      i0.\u0275\u0275advance(2);
      i0.\u0275\u0275textInterpolate(ctx.mode === "login" ? i0.\u0275\u0275pipeBind1(13, 6, "auth.register") : i0.\u0275\u0275pipeBind1(14, 8, "auth.signIn"));
      i0.\u0275\u0275advance(3);
      i0.\u0275\u0275property("ngIf", ctx.mode === "login");
      i0.\u0275\u0275advance();
      i0.\u0275\u0275property("ngIf", ctx.mode === "register");
    }
  }, dependencies: [i1.NgClass, i1.NgComponentOutlet, i1.NgForOf, i1.NgIf, i1.NgTemplateOutlet, i1.NgStyle, i1.NgSwitch, i1.NgSwitchCase, i1.NgSwitchDefault, i1.NgPlural, i1.NgPluralCase, i2.\u0275NgNoValidate, i2.NgSelectOption, i2.\u0275NgSelectMultipleOption, i2.DefaultValueAccessor, i2.NumberValueAccessor, i2.RangeValueAccessor, i2.CheckboxControlValueAccessor, i2.SelectControlValueAccessor, i2.SelectMultipleControlValueAccessor, i2.RadioControlValueAccessor, i2.NgControlStatus, i2.NgControlStatusGroup, i2.RequiredValidator, i2.MinLengthValidator, i2.MaxLengthValidator, i2.PatternValidator, i2.CheckboxRequiredValidator, i2.EmailValidator, i2.MinValidator, i2.MaxValidator, i2.NgModel, i2.NgModelGroup, i2.NgForm, i2.FormControlDirective, i2.FormGroupDirective, i2.FormControlName, i2.FormGroupName, i2.FormArrayName, i3.RouterOutlet, i3.RouterLink, i3.RouterLinkActive, i3.\u0275EmptyOutletComponent, i4.NgbAccordionButton, i4.NgbAccordionDirective, i4.NgbAccordionItem, i4.NgbAccordionHeader, i4.NgbAccordionToggle, i4.NgbAccordionBody, i4.NgbAccordionCollapse, i4.NgbAlert, i4.NgbCarousel, i4.NgbSlide, i4.NgbCollapse, i4.NgbDatepicker, i4.NgbDatepickerContent, i4.NgbInputDatepicker, i4.NgbDatepickerMonth, i4.NgbDropdown, i4.NgbDropdownAnchor, i4.NgbDropdownToggle, i4.NgbDropdownMenu, i4.NgbDropdownItem, i4.NgbDropdownButtonItem, i4.NgbNavContent, i4.NgbNav, i4.NgbNavItem, i4.NgbNavItemRole, i4.NgbNavLink, i4.NgbNavLinkButton, i4.NgbNavLinkBase, i4.NgbNavOutlet, i4.NgbNavPane, i4.NgbPagination, i4.NgbPaginationEllipsis, i4.NgbPaginationFirst, i4.NgbPaginationLast, i4.NgbPaginationNext, i4.NgbPaginationNumber, i4.NgbPaginationPrevious, i4.NgbPaginationPages, i4.NgbPopover, i4.NgbProgressbar, i4.NgbProgressbarStacked, i4.NgbRating, i4.NgbScrollSpy, i4.NgbScrollSpyItem, i4.NgbScrollSpyFragment, i4.NgbScrollSpyMenu, i4.NgbTimepicker, i4.NgbToast, i4.NgbToastHeader, i4.NgbTooltip, i4.NgbHighlight, i4.NgbTypeahead, i5.TranslateDirective, i6.BaseChartDirective, PatientTabBarComponent, GlassCardComponent, GlassButtonDirective, GlassInputComponent, GlassToolbarComponent, GlassTabbarComponent, i1.AsyncPipe, i1.UpperCasePipe, i1.LowerCasePipe, i1.JsonPipe, i1.SlicePipe, i1.DecimalPipe, i1.PercentPipe, i1.TitleCasePipe, i1.CurrencyPipe, i1.DatePipe, i1.I18nPluralPipe, i1.I18nSelectPipe, i1.KeyValuePipe, i5.TranslatePipe], styles: ["\n\n[_nghost-%COMP%] {\n  display: block;\n}\n.auth-shell[_ngcontent-%COMP%] {\n  min-height: calc(100svh - 6rem);\n  display: flex;\n  align-items: center;\n  justify-content: center;\n  padding: 3rem 1.5rem 4rem;\n}\n.loader-dot[_ngcontent-%COMP%] {\n  display: inline-block;\n  width: 0.85rem;\n  height: 0.85rem;\n  border-radius: 999px;\n  background: var(--accent);\n  margin-right: 0.5rem;\n  animation: _ngcontent-%COMP%_pulse 1s infinite ease-in-out;\n}\n@keyframes _ngcontent-%COMP%_pulse {\n  0%, 100% {\n    opacity: 0.2;\n    transform: scale(0.9);\n  }\n  50% {\n    opacity: 1;\n    transform: scale(1.1);\n  }\n}\n/*# sourceMappingURL=auth-page.component.css.map */"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i0.\u0275setClassMetadata(AuthPageComponent, [{
    type: Component,
    args: [{ selector: "app-auth-page", standalone: false, template: `<div class="auth-shell">
  <app-glass-card [extraClass]="'w-full max-w-xl glass-strong space-y-6'">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl sm:text-3xl font-semibold text-[var(--text)]">Medic Insight</h1>
        <p class="text-sm text-[var(--text-dim)]">
          {{ mode === 'login' ? 'Welcome back! Sign in to continue.' : 'Create an account to share your analyses and trends.' }}
        </p>
      </div>
      <button type="button" appGlassButton (click)="toggleMode()">
        <span class="material-symbols-rounded">{{ mode === 'login' ? 'person_add' : 'login' }}</span>
        <span>{{ mode === 'login' ? ('auth.register' | translate) : ('auth.signIn' | translate) }}</span>
      </button>
    </div>

    <form *ngIf="mode === 'login'" [formGroup]="loginForm" (ngSubmit)="submitLogin()" class="space-y-5">
      <app-glass-input [label]="'auth.email' | translate" placeholder="you@example.com" type="email" formControlName="email"></app-glass-input>
      <app-glass-input [label]="'auth.password' | translate" placeholder="Enter password" type="password" formControlName="password"></app-glass-input>

      <div *ngIf="errorMessage" class="toast-glass error" role="alert">
        <span class="material-symbols-rounded">error</span>
        <span>{{ errorMessage }}</span>
      </div>

      <button type="submit" appGlassButton [glassBlock]="true" [disabled]="isSubmitting">
        <span *ngIf="isSubmitting" class="loader-dot"></span>
        <span>{{ isSubmitting ? ('auth.signingIn' | translate) : ('auth.signInBtn' | translate) }}</span>
      </button>
    </form>

    <form *ngIf="mode === 'register'" [formGroup]="registerForm" (ngSubmit)="submitRegister()" class="space-y-5">
      <app-glass-input [label]="'auth.email' | translate" placeholder="you@example.com" type="email" formControlName="email"></app-glass-input>
      <app-glass-input [label]="'auth.password' | translate" placeholder="Minimum 8 characters" type="password" formControlName="password"></app-glass-input>
      <app-glass-input [label]="'auth.confirmPassword' | translate" placeholder="Repeat the password" type="password" formControlName="confirmPassword"></app-glass-input>

      <div class="flex flex-col gap-2">
        <label class="text-xs uppercase tracking-[0.2em] text-[var(--text-dim)]">{{ 'auth.role' | translate }}</label>
        <select class="input-glass" formControlName="role">
          <option value="PATIENT">{{ 'auth.patient' | translate }}</option>
          <option value="DOCTOR">{{ 'auth.doctor' | translate }}</option>
        </select>
      </div>

      <div *ngIf="errorMessage" class="toast-glass error" role="alert">
        <span class="material-symbols-rounded">error</span>
        <span>{{ errorMessage }}</span>
      </div>

      <button type="submit" appGlassButton [glassBlock]="true" [disabled]="isSubmitting">
        <span *ngIf="isSubmitting" class="loader-dot"></span>
        <span>{{ isSubmitting ? ('auth.creating' | translate) : ('auth.createBtn' | translate) }}</span>
      </button>
    </form>
  </app-glass-card>
</div>
`, styles: ["/* src/app/features/auth/pages/auth-page/auth-page.component.scss */\n:host {\n  display: block;\n}\n.auth-shell {\n  min-height: calc(100svh - 6rem);\n  display: flex;\n  align-items: center;\n  justify-content: center;\n  padding: 3rem 1.5rem 4rem;\n}\n.loader-dot {\n  display: inline-block;\n  width: 0.85rem;\n  height: 0.85rem;\n  border-radius: 999px;\n  background: var(--accent);\n  margin-right: 0.5rem;\n  animation: pulse 1s infinite ease-in-out;\n}\n@keyframes pulse {\n  0%, 100% {\n    opacity: 0.2;\n    transform: scale(0.9);\n  }\n  50% {\n    opacity: 1;\n    transform: scale(1.1);\n  }\n}\n/*# sourceMappingURL=auth-page.component.css.map */\n"] }]
  }], null, null);
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i0.\u0275setClassDebugInfo(AuthPageComponent, { className: "AuthPageComponent", filePath: "src/app/features/auth/pages/auth-page/auth-page.component.ts", lineNumber: 14 });
})();
(() => {
  const id = "src%2Fapp%2Ffeatures%2Fauth%2Fpages%2Fauth-page%2Fauth-page.component.ts%40AuthPageComponent";
  function AuthPageComponent_HmrLoad(t) {
    import(
      /* @vite-ignore */
      __vite__injectQuery(i0.\u0275\u0275getReplaceMetadataURL(id, t, import.meta.url), 'import')
    ).then((m) => m.default && i0.\u0275\u0275replaceMetadata(AuthPageComponent, m.default, [i0, i1, i2, i3, i4, i5, i6, patient_tab_bar_component_exports, glass_card_component_exports, glass_button_directive_exports, glass_input_component_exports, glass_toolbar_component_exports, glass_tabbar_component_exports], [Component], import.meta, id));
  }
  (typeof ngDevMode === "undefined" || ngDevMode) && AuthPageComponent_HmrLoad(Date.now());
  (typeof ngDevMode === "undefined" || ngDevMode) && (import.meta.hot && import.meta.hot.on("angular:component-update", (d) => d.id === id && AuthPageComponent_HmrLoad(d.timestamp)));
})();

// src/app/features/auth/auth-routing.module.ts
import * as i02 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import * as i12 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
var routes = [
  {
    path: "",
    component: AuthPageComponent,
    data: {
      title: "Sign in or sign up",
      subtitle: "Secure access to your lab data",
      hideToolbar: true
    }
  }
];
var AuthRoutingModule = class _AuthRoutingModule {
  static \u0275fac = function AuthRoutingModule_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _AuthRoutingModule)();
  };
  static \u0275mod = /* @__PURE__ */ i02.\u0275\u0275defineNgModule({ type: _AuthRoutingModule });
  static \u0275inj = /* @__PURE__ */ i02.\u0275\u0275defineInjector({ imports: [RouterModule.forChild(routes), RouterModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i02.\u0275setClassMetadata(AuthRoutingModule, [{
    type: NgModule,
    args: [{
      imports: [RouterModule.forChild(routes)],
      exports: [RouterModule]
    }]
  }], null, null);
})();

// src/app/features/auth/auth.module.ts
import * as i03 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
var AuthModule = class _AuthModule {
  static \u0275fac = function AuthModule_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _AuthModule)();
  };
  static \u0275mod = /* @__PURE__ */ i03.\u0275\u0275defineNgModule({ type: _AuthModule });
  static \u0275inj = /* @__PURE__ */ i03.\u0275\u0275defineInjector({ imports: [SharedModule, AuthRoutingModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i03.\u0275setClassMetadata(AuthModule, [{
    type: NgModule2,
    args: [{
      declarations: [AuthPageComponent],
      imports: [SharedModule, AuthRoutingModule]
    }]
  }], null, null);
})();
export {
  AuthModule
};


//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbInNyYy9hcHAvZmVhdHVyZXMvYXV0aC9hdXRoLm1vZHVsZS50cyIsInNyYy9hcHAvZmVhdHVyZXMvYXV0aC9hdXRoLXJvdXRpbmcubW9kdWxlLnRzIiwic3JjL2FwcC9mZWF0dXJlcy9hdXRoL3BhZ2VzL2F1dGgtcGFnZS9hdXRoLXBhZ2UuY29tcG9uZW50LnRzIiwic3JjL2FwcC9mZWF0dXJlcy9hdXRoL3BhZ2VzL2F1dGgtcGFnZS9hdXRoLXBhZ2UuY29tcG9uZW50Lmh0bWwiXSwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IHsgTmdNb2R1bGUgfSBmcm9tICdAYW5ndWxhci9jb3JlJztcblxuaW1wb3J0IHsgU2hhcmVkTW9kdWxlIH0gZnJvbSAnLi4vLi4vc2hhcmVkL3NoYXJlZC5tb2R1bGUnO1xuaW1wb3J0IHsgQXV0aFJvdXRpbmdNb2R1bGUgfSBmcm9tICcuL2F1dGgtcm91dGluZy5tb2R1bGUnO1xuaW1wb3J0IHsgQXV0aFBhZ2VDb21wb25lbnQgfSBmcm9tICcuL3BhZ2VzL2F1dGgtcGFnZS9hdXRoLXBhZ2UuY29tcG9uZW50JztcblxuQE5nTW9kdWxlKHtcbiAgZGVjbGFyYXRpb25zOiBbQXV0aFBhZ2VDb21wb25lbnRdLFxuICBpbXBvcnRzOiBbU2hhcmVkTW9kdWxlLCBBdXRoUm91dGluZ01vZHVsZV0sXG59KVxuZXhwb3J0IGNsYXNzIEF1dGhNb2R1bGUge31cblxyXG4iLCJpbXBvcnQgeyBOZ01vZHVsZSB9IGZyb20gJ0Bhbmd1bGFyL2NvcmUnO1xuaW1wb3J0IHsgUm91dGVyTW9kdWxlLCBSb3V0ZXMgfSBmcm9tICdAYW5ndWxhci9yb3V0ZXInO1xuXG5pbXBvcnQgeyBBdXRoUGFnZUNvbXBvbmVudCB9IGZyb20gJy4vcGFnZXMvYXV0aC1wYWdlL2F1dGgtcGFnZS5jb21wb25lbnQnO1xuXG5jb25zdCByb3V0ZXM6IFJvdXRlcyA9IFtcbiAge1xuICAgIHBhdGg6ICcnLFxuICAgIGNvbXBvbmVudDogQXV0aFBhZ2VDb21wb25lbnQsXG4gICAgZGF0YToge1xuICAgICAgdGl0bGU6ICdTaWduIGluIG9yIHNpZ24gdXAnLFxuICAgICAgc3VidGl0bGU6ICdTZWN1cmUgYWNjZXNzIHRvIHlvdXIgbGFiIGRhdGEnLFxuICAgICAgaGlkZVRvb2xiYXI6IHRydWUsXG4gICAgfSxcbiAgfSxcbl07XG5cbkBOZ01vZHVsZSh7XG4gIGltcG9ydHM6IFtSb3V0ZXJNb2R1bGUuZm9yQ2hpbGQocm91dGVzKV0sXG4gIGV4cG9ydHM6IFtSb3V0ZXJNb2R1bGVdLFxufSlcbmV4cG9ydCBjbGFzcyBBdXRoUm91dGluZ01vZHVsZSB7fVxuIiwiaW1wb3J0IHsgQ29tcG9uZW50LCBPbkluaXQsIGluamVjdCB9IGZyb20gJ0Bhbmd1bGFyL2NvcmUnO1xuaW1wb3J0IHsgRm9ybUJ1aWxkZXIsIFZhbGlkYXRvcnMgfSBmcm9tICdAYW5ndWxhci9mb3Jtcyc7XG5pbXBvcnQgeyBSb3V0ZXIgfSBmcm9tICdAYW5ndWxhci9yb3V0ZXInO1xuXG5pbXBvcnQgeyBBdXRoU2VydmljZSB9IGZyb20gJy4uLy4uLy4uLy4uL2NvcmUvc2VydmljZXMvYXV0aC5zZXJ2aWNlJztcbmltcG9ydCB7IFVzZXIgfSBmcm9tICcuLi8uLi8uLi8uLi9jb3JlL21vZGVscy91c2VyLm1vZGVsJztcblxuQENvbXBvbmVudCh7XG4gIHNlbGVjdG9yOiAnYXBwLWF1dGgtcGFnZScsXG4gIHN0YW5kYWxvbmU6IGZhbHNlLFxuICB0ZW1wbGF0ZVVybDogJy4vYXV0aC1wYWdlLmNvbXBvbmVudC5odG1sJyxcbiAgc3R5bGVVcmxzOiBbJy4vYXV0aC1wYWdlLmNvbXBvbmVudC5zY3NzJ10sXG59KVxuZXhwb3J0IGNsYXNzIEF1dGhQYWdlQ29tcG9uZW50IGltcGxlbWVudHMgT25Jbml0IHtcbiAgcHJpdmF0ZSByZWFkb25seSBmYiA9IGluamVjdChGb3JtQnVpbGRlcik7XG4gIHByaXZhdGUgcmVhZG9ubHkgYXV0aCA9IGluamVjdChBdXRoU2VydmljZSk7XG4gIHByaXZhdGUgcmVhZG9ubHkgcm91dGVyID0gaW5qZWN0KFJvdXRlcik7XG5cbiAgbW9kZTogJ2xvZ2luJyB8ICdyZWdpc3RlcicgPSAnbG9naW4nO1xuICBpc1N1Ym1pdHRpbmcgPSBmYWxzZTtcbiAgZXJyb3JNZXNzYWdlID0gJyc7XG5cbiAgcmVhZG9ubHkgbG9naW5Gb3JtID0gdGhpcy5mYi5ub25OdWxsYWJsZS5ncm91cCh7XG4gICAgZW1haWw6IFsnJywgW1ZhbGlkYXRvcnMucmVxdWlyZWQsIFZhbGlkYXRvcnMuZW1haWxdXSxcbiAgICBwYXNzd29yZDogWycnLCBbVmFsaWRhdG9ycy5yZXF1aXJlZCwgVmFsaWRhdG9ycy5taW5MZW5ndGgoOCldXSxcbiAgfSk7XG5cbiAgcmVhZG9ubHkgcmVnaXN0ZXJGb3JtID0gdGhpcy5mYi5ub25OdWxsYWJsZS5ncm91cCh7XG4gICAgZW1haWw6IFsnJywgW1ZhbGlkYXRvcnMucmVxdWlyZWQsIFZhbGlkYXRvcnMuZW1haWxdXSxcbiAgICBwYXNzd29yZDogWycnLCBbVmFsaWRhdG9ycy5yZXF1aXJlZCwgVmFsaWRhdG9ycy5taW5MZW5ndGgoOCldXSxcbiAgICBjb25maXJtUGFzc3dvcmQ6IFsnJywgW1ZhbGlkYXRvcnMucmVxdWlyZWRdXSxcbiAgICByb2xlOiBbJ1BBVElFTlQnXSxcbiAgfSk7XG5cbiAgbmdPbkluaXQoKTogdm9pZCB7XG4gICAgdGhpcy5hdXRoLmxvYWRQcm9maWxlKCkuc3Vic2NyaWJlKCh1c2VyKSA9PiB7XG4gICAgICBpZiAodXNlcikge1xuICAgICAgICB0aGlzLnJlZGlyZWN0QWZ0ZXJBdXRoKHVzZXIpO1xuICAgICAgfVxuICAgIH0pO1xuICB9XG5cbiAgdG9nZ2xlTW9kZSgpOiB2b2lkIHtcbiAgICB0aGlzLm1vZGUgPSB0aGlzLm1vZGUgPT09ICdsb2dpbicgPyAncmVnaXN0ZXInIDogJ2xvZ2luJztcbiAgICB0aGlzLmVycm9yTWVzc2FnZSA9ICcnO1xuICB9XG5cbiAgc3VibWl0TG9naW4oKTogdm9pZCB7XG4gICAgaWYgKHRoaXMubG9naW5Gb3JtLmludmFsaWQpIHtcbiAgICAgIHRoaXMubG9naW5Gb3JtLm1hcmtBbGxBc1RvdWNoZWQoKTtcbiAgICAgIHJldHVybjtcbiAgICB9XG5cbiAgICB0aGlzLmlzU3VibWl0dGluZyA9IHRydWU7XG4gICAgdGhpcy5lcnJvck1lc3NhZ2UgPSAnJztcbiAgICB0aGlzLmF1dGgubG9naW4odGhpcy5sb2dpbkZvcm0uZ2V0UmF3VmFsdWUoKSkuc3Vic2NyaWJlKHtcbiAgICAgIG5leHQ6ICh1c2VyKSA9PiB0aGlzLnJlZGlyZWN0QWZ0ZXJBdXRoKHVzZXIpLFxuICAgICAgZXJyb3I6IChlcnIpID0+IHtcbiAgICAgICAgdGhpcy5lcnJvck1lc3NhZ2UgPSBlcnI/LmVycm9yPy5kZXRhaWwgPz8gJ1VuYWJsZSB0byBzaWduIGluLiBDaGVjayB5b3VyIGVtYWlsIGFuZCBwYXNzd29yZC4nO1xuICAgICAgICB0aGlzLmlzU3VibWl0dGluZyA9IGZhbHNlO1xuICAgICAgfSxcbiAgICAgIGNvbXBsZXRlOiAoKSA9PiAodGhpcy5pc1N1Ym1pdHRpbmcgPSBmYWxzZSksXG4gICAgfSk7XG4gIH1cblxuICBzdWJtaXRSZWdpc3RlcigpOiB2b2lkIHtcbiAgICBpZiAodGhpcy5yZWdpc3RlckZvcm0uaW52YWxpZCB8fCB0aGlzLnJlZ2lzdGVyRm9ybS52YWx1ZS5wYXNzd29yZCAhPT0gdGhpcy5yZWdpc3RlckZvcm0udmFsdWUuY29uZmlybVBhc3N3b3JkKSB7XG4gICAgICB0aGlzLnJlZ2lzdGVyRm9ybS5tYXJrQWxsQXNUb3VjaGVkKCk7XG4gICAgICBpZiAodGhpcy5yZWdpc3RlckZvcm0udmFsdWUucGFzc3dvcmQgIT09IHRoaXMucmVnaXN0ZXJGb3JtLnZhbHVlLmNvbmZpcm1QYXNzd29yZCkge1xuICAgICAgICB0aGlzLmVycm9yTWVzc2FnZSA9ICdQYXNzd29yZHMgbXVzdCBtYXRjaC4nO1xuICAgICAgfVxuICAgICAgcmV0dXJuO1xuICAgIH1cblxuICAgIHRoaXMuaXNTdWJtaXR0aW5nID0gdHJ1ZTtcbiAgICB0aGlzLmVycm9yTWVzc2FnZSA9ICcnO1xuICAgIGNvbnN0IHsgZW1haWwsIHBhc3N3b3JkLCByb2xlIH0gPSB0aGlzLnJlZ2lzdGVyRm9ybS5nZXRSYXdWYWx1ZSgpO1xuICAgIHRoaXMuYXV0aC5yZWdpc3Rlcih7IGVtYWlsLCBwYXNzd29yZCwgcm9sZSB9KS5zdWJzY3JpYmUoe1xuICAgICAgbmV4dDogKHVzZXIpID0+IHRoaXMucmVkaXJlY3RBZnRlckF1dGgodXNlciksXG4gICAgICBlcnJvcjogKGVycikgPT4ge1xuICAgICAgICB0aGlzLmVycm9yTWVzc2FnZSA9IGVycj8uZXJyb3I/LmRldGFpbCA/PyAnUmVnaXN0cmF0aW9uIGZhaWxlZC4gUGxlYXNlIHRyeSBhZ2Fpbi4nO1xuICAgICAgICB0aGlzLmlzU3VibWl0dGluZyA9IGZhbHNlO1xuICAgICAgfSxcbiAgICAgIGNvbXBsZXRlOiAoKSA9PiAodGhpcy5pc1N1Ym1pdHRpbmcgPSBmYWxzZSksXG4gICAgfSk7XG4gIH1cblxuICBwcml2YXRlIHJlZGlyZWN0QWZ0ZXJBdXRoKHVzZXI6IFVzZXIpOiB2b2lkIHtcbiAgICBjb25zdCBpc0RvY3RvciA9IHVzZXIucm9sZSA9PT0gJ0RPQ1RPUicgfHwgdXNlci5pc19kb2N0b3IgPT09IHRydWU7XG4gICAgY29uc3QgdGFyZ2V0ID0gaXNEb2N0b3IgPyAnL2RvY3RvcicgOiAnL3BhdGllbnQnO1xuICAgIHZvaWQgdGhpcy5yb3V0ZXIubmF2aWdhdGVCeVVybCh0YXJnZXQpO1xuICB9XG59XG4iLCI8ZGl2IGNsYXNzPVwiYXV0aC1zaGVsbFwiPlxuICA8YXBwLWdsYXNzLWNhcmQgW2V4dHJhQ2xhc3NdPVwiJ3ctZnVsbCBtYXgtdy14bCBnbGFzcy1zdHJvbmcgc3BhY2UteS02J1wiPlxuICAgIDxkaXYgY2xhc3M9XCJmbGV4IGl0ZW1zLWNlbnRlciBqdXN0aWZ5LWJldHdlZW5cIj5cbiAgICAgIDxkaXY+XG4gICAgICAgIDxoMSBjbGFzcz1cInRleHQtMnhsIHNtOnRleHQtM3hsIGZvbnQtc2VtaWJvbGQgdGV4dC1bdmFyKC0tdGV4dCldXCI+TWVkaWMgSW5zaWdodDwvaDE+XG4gICAgICAgIDxwIGNsYXNzPVwidGV4dC1zbSB0ZXh0LVt2YXIoLS10ZXh0LWRpbSldXCI+XG4gICAgICAgICAge3sgbW9kZSA9PT0gJ2xvZ2luJyA/ICdXZWxjb21lIGJhY2shIFNpZ24gaW4gdG8gY29udGludWUuJyA6ICdDcmVhdGUgYW4gYWNjb3VudCB0byBzaGFyZSB5b3VyIGFuYWx5c2VzIGFuZCB0cmVuZHMuJyB9fVxuICAgICAgICA8L3A+XG4gICAgICA8L2Rpdj5cbiAgICAgIDxidXR0b24gdHlwZT1cImJ1dHRvblwiIGFwcEdsYXNzQnV0dG9uIChjbGljayk9XCJ0b2dnbGVNb2RlKClcIj5cbiAgICAgICAgPHNwYW4gY2xhc3M9XCJtYXRlcmlhbC1zeW1ib2xzLXJvdW5kZWRcIj57eyBtb2RlID09PSAnbG9naW4nID8gJ3BlcnNvbl9hZGQnIDogJ2xvZ2luJyB9fTwvc3Bhbj5cbiAgICAgICAgPHNwYW4+e3sgbW9kZSA9PT0gJ2xvZ2luJyA/ICgnYXV0aC5yZWdpc3RlcicgfCB0cmFuc2xhdGUpIDogKCdhdXRoLnNpZ25JbicgfCB0cmFuc2xhdGUpIH19PC9zcGFuPlxuICAgICAgPC9idXR0b24+XG4gICAgPC9kaXY+XG5cbiAgICA8Zm9ybSAqbmdJZj1cIm1vZGUgPT09ICdsb2dpbidcIiBbZm9ybUdyb3VwXT1cImxvZ2luRm9ybVwiIChuZ1N1Ym1pdCk9XCJzdWJtaXRMb2dpbigpXCIgY2xhc3M9XCJzcGFjZS15LTVcIj5cbiAgICAgIDxhcHAtZ2xhc3MtaW5wdXQgW2xhYmVsXT1cIidhdXRoLmVtYWlsJyB8IHRyYW5zbGF0ZVwiIHBsYWNlaG9sZGVyPVwieW91QGV4YW1wbGUuY29tXCIgdHlwZT1cImVtYWlsXCIgZm9ybUNvbnRyb2xOYW1lPVwiZW1haWxcIj48L2FwcC1nbGFzcy1pbnB1dD5cbiAgICAgIDxhcHAtZ2xhc3MtaW5wdXQgW2xhYmVsXT1cIidhdXRoLnBhc3N3b3JkJyB8IHRyYW5zbGF0ZVwiIHBsYWNlaG9sZGVyPVwiRW50ZXIgcGFzc3dvcmRcIiB0eXBlPVwicGFzc3dvcmRcIiBmb3JtQ29udHJvbE5hbWU9XCJwYXNzd29yZFwiPjwvYXBwLWdsYXNzLWlucHV0PlxuXG4gICAgICA8ZGl2ICpuZ0lmPVwiZXJyb3JNZXNzYWdlXCIgY2xhc3M9XCJ0b2FzdC1nbGFzcyBlcnJvclwiIHJvbGU9XCJhbGVydFwiPlxuICAgICAgICA8c3BhbiBjbGFzcz1cIm1hdGVyaWFsLXN5bWJvbHMtcm91bmRlZFwiPmVycm9yPC9zcGFuPlxuICAgICAgICA8c3Bhbj57eyBlcnJvck1lc3NhZ2UgfX08L3NwYW4+XG4gICAgICA8L2Rpdj5cblxuICAgICAgPGJ1dHRvbiB0eXBlPVwic3VibWl0XCIgYXBwR2xhc3NCdXR0b24gW2dsYXNzQmxvY2tdPVwidHJ1ZVwiIFtkaXNhYmxlZF09XCJpc1N1Ym1pdHRpbmdcIj5cbiAgICAgICAgPHNwYW4gKm5nSWY9XCJpc1N1Ym1pdHRpbmdcIiBjbGFzcz1cImxvYWRlci1kb3RcIj48L3NwYW4+XG4gICAgICAgIDxzcGFuPnt7IGlzU3VibWl0dGluZyA/ICgnYXV0aC5zaWduaW5nSW4nIHwgdHJhbnNsYXRlKSA6ICgnYXV0aC5zaWduSW5CdG4nIHwgdHJhbnNsYXRlKSB9fTwvc3Bhbj5cbiAgICAgIDwvYnV0dG9uPlxuICAgIDwvZm9ybT5cblxuICAgIDxmb3JtICpuZ0lmPVwibW9kZSA9PT0gJ3JlZ2lzdGVyJ1wiIFtmb3JtR3JvdXBdPVwicmVnaXN0ZXJGb3JtXCIgKG5nU3VibWl0KT1cInN1Ym1pdFJlZ2lzdGVyKClcIiBjbGFzcz1cInNwYWNlLXktNVwiPlxuICAgICAgPGFwcC1nbGFzcy1pbnB1dCBbbGFiZWxdPVwiJ2F1dGguZW1haWwnIHwgdHJhbnNsYXRlXCIgcGxhY2Vob2xkZXI9XCJ5b3VAZXhhbXBsZS5jb21cIiB0eXBlPVwiZW1haWxcIiBmb3JtQ29udHJvbE5hbWU9XCJlbWFpbFwiPjwvYXBwLWdsYXNzLWlucHV0PlxuICAgICAgPGFwcC1nbGFzcy1pbnB1dCBbbGFiZWxdPVwiJ2F1dGgucGFzc3dvcmQnIHwgdHJhbnNsYXRlXCIgcGxhY2Vob2xkZXI9XCJNaW5pbXVtIDggY2hhcmFjdGVyc1wiIHR5cGU9XCJwYXNzd29yZFwiIGZvcm1Db250cm9sTmFtZT1cInBhc3N3b3JkXCI+PC9hcHAtZ2xhc3MtaW5wdXQ+XG4gICAgICA8YXBwLWdsYXNzLWlucHV0IFtsYWJlbF09XCInYXV0aC5jb25maXJtUGFzc3dvcmQnIHwgdHJhbnNsYXRlXCIgcGxhY2Vob2xkZXI9XCJSZXBlYXQgdGhlIHBhc3N3b3JkXCIgdHlwZT1cInBhc3N3b3JkXCIgZm9ybUNvbnRyb2xOYW1lPVwiY29uZmlybVBhc3N3b3JkXCI+PC9hcHAtZ2xhc3MtaW5wdXQ+XG5cbiAgICAgIDxkaXYgY2xhc3M9XCJmbGV4IGZsZXgtY29sIGdhcC0yXCI+XG4gICAgICAgIDxsYWJlbCBjbGFzcz1cInRleHQteHMgdXBwZXJjYXNlIHRyYWNraW5nLVswLjJlbV0gdGV4dC1bdmFyKC0tdGV4dC1kaW0pXVwiPnt7ICdhdXRoLnJvbGUnIHwgdHJhbnNsYXRlIH19PC9sYWJlbD5cbiAgICAgICAgPHNlbGVjdCBjbGFzcz1cImlucHV0LWdsYXNzXCIgZm9ybUNvbnRyb2xOYW1lPVwicm9sZVwiPlxuICAgICAgICAgIDxvcHRpb24gdmFsdWU9XCJQQVRJRU5UXCI+e3sgJ2F1dGgucGF0aWVudCcgfCB0cmFuc2xhdGUgfX08L29wdGlvbj5cbiAgICAgICAgICA8b3B0aW9uIHZhbHVlPVwiRE9DVE9SXCI+e3sgJ2F1dGguZG9jdG9yJyB8IHRyYW5zbGF0ZSB9fTwvb3B0aW9uPlxuICAgICAgICA8L3NlbGVjdD5cbiAgICAgIDwvZGl2PlxuXG4gICAgICA8ZGl2ICpuZ0lmPVwiZXJyb3JNZXNzYWdlXCIgY2xhc3M9XCJ0b2FzdC1nbGFzcyBlcnJvclwiIHJvbGU9XCJhbGVydFwiPlxuICAgICAgICA8c3BhbiBjbGFzcz1cIm1hdGVyaWFsLXN5bWJvbHMtcm91bmRlZFwiPmVycm9yPC9zcGFuPlxuICAgICAgICA8c3Bhbj57eyBlcnJvck1lc3NhZ2UgfX08L3NwYW4+XG4gICAgICA8L2Rpdj5cblxuICAgICAgPGJ1dHRvbiB0eXBlPVwic3VibWl0XCIgYXBwR2xhc3NCdXR0b24gW2dsYXNzQmxvY2tdPVwidHJ1ZVwiIFtkaXNhYmxlZF09XCJpc1N1Ym1pdHRpbmdcIj5cbiAgICAgICAgPHNwYW4gKm5nSWY9XCJpc1N1Ym1pdHRpbmdcIiBjbGFzcz1cImxvYWRlci1kb3RcIj48L3NwYW4+XG4gICAgICAgIDxzcGFuPnt7IGlzU3VibWl0dGluZyA/ICgnYXV0aC5jcmVhdGluZycgfCB0cmFuc2xhdGUpIDogKCdhdXRoLmNyZWF0ZUJ0bicgfCB0cmFuc2xhdGUpIH19PC9zcGFuPlxuICAgICAgPC9idXR0b24+XG4gICAgPC9mb3JtPlxuICA8L2FwcC1nbGFzcy1jYXJkPlxuPC9kaXY+XG4iXSwibWFwcGluZ3MiOiI7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBQSxTQUFTLFlBQUFBLGlCQUFnQjs7O0FDQXpCLFNBQVMsZ0JBQWdCO0FBQ3pCLFNBQVMsb0JBQTRCOzs7QUNEckMsU0FBUyxXQUFtQixjQUFjO0FBQzFDLFNBQVMsYUFBYSxrQkFBa0I7QUFDeEMsU0FBUyxjQUFjO0E7Ozs7Ozs7OztBQ2lCakIsSUFBQSw0QkFBQSxHQUFBLE9BQUEsRUFBQSxFQUFpRSxHQUFBLFFBQUEsQ0FBQTtBQUN4QixJQUFBLG9CQUFBLEdBQUEsT0FBQTtBQUFLLElBQUEsMEJBQUE7QUFDNUMsSUFBQSw0QkFBQSxHQUFBLE1BQUE7QUFBTSxJQUFBLG9CQUFBLENBQUE7QUFBa0IsSUFBQSwwQkFBQSxFQUFPOzs7O0FBQXpCLElBQUEsdUJBQUEsQ0FBQTtBQUFBLElBQUEsK0JBQUEsT0FBQSxZQUFBOzs7OztBQUlOLElBQUEsdUJBQUEsR0FBQSxRQUFBLEVBQUE7Ozs7OztBQVZKLElBQUEsNEJBQUEsR0FBQSxRQUFBLENBQUE7QUFBdUQsSUFBQSx3QkFBQSxZQUFBLFNBQUEsOERBQUE7QUFBQSxNQUFBLDJCQUFBLEdBQUE7QUFBQSxZ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