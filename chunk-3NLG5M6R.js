import { injectQuery as __vite__injectQuery } from "/@vite/client";import { createHotContext as __vite__createHotContext } from "/@vite/client";import.meta.hot = __vite__createHotContext("/chunk-3NLG5M6R.js");import {
  DoctorService
} from "/chunk-TO7YSHKU.js";
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
  __export,
  glass_button_directive_exports,
  glass_tabbar_component_exports,
  glass_toolbar_component_exports
} from "/chunk-BM63WUAP.js";

// src/app/features/doctor/doctor.module.ts
import { NgModule as NgModule2 } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";

// src/app/features/doctor/doctor-routing.module.ts
import { NgModule } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import { RouterModule } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";

// src/app/features/doctor/pages/patients/doctor-patients-page.component.ts
import { Component as Component2, inject as inject2 } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import { Router } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
import * as i02 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import * as i1 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_common.js?v=24701eb5";
import * as i2 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_forms.js?v=24701eb5";
import * as i3 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
import * as i4 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@ng-bootstrap_ng-bootstrap.js?v=24701eb5";
import * as i5 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@ngx-translate_core.js?v=24701eb5";
import * as i6 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/ng2-charts.js?v=24701eb5";

// src/app/features/doctor/pages/patient-detail/doctor-patient-detail-page.component.ts
var doctor_patient_detail_page_component_exports = {};
__export(doctor_patient_detail_page_component_exports, {
  DoctorPatientDetailPageComponent: () => DoctorPatientDetailPageComponent
});
import { Component, ViewChild, inject } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import { ActivatedRoute } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
import { BaseChartDirective } from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/ng2-charts.js?v=24701eb5";
import Chart from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/chart__js_auto.js?v=24701eb5";
import zoomPlugin from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/chartjs-plugin-zoom.js?v=24701eb5";
import "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/chartjs-adapter-date-fns.js?v=24701eb5";
import * as i0 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
function DoctorPatientDetailPageComponent_option_15_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275elementStart(0, "option", 12);
    i0.\u0275\u0275text(1);
    i0.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    const option_r1 = ctx.$implicit;
    i0.\u0275\u0275property("ngValue", option_r1);
    i0.\u0275\u0275advance();
    i0.\u0275\u0275textInterpolate(option_r1);
  }
}
function DoctorPatientDetailPageComponent_div_16_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275elementStart(0, "div", 13);
    i0.\u0275\u0275element(1, "div", 14);
    i0.\u0275\u0275text(2);
    i0.\u0275\u0275pipe(3, "translate");
    i0.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    i0.\u0275\u0275advance(2);
    i0.\u0275\u0275textInterpolate1(" ", i0.\u0275\u0275pipeBind1(3, 1, "doctor.loading"), " ");
  }
}
function DoctorPatientDetailPageComponent_div_17_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275elementStart(0, "div", 15);
    i0.\u0275\u0275text(1);
    i0.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    const ctx_r1 = i0.\u0275\u0275nextContext();
    i0.\u0275\u0275advance();
    i0.\u0275\u0275textInterpolate1(" ", ctx_r1.errorMessage, " ");
  }
}
function DoctorPatientDetailPageComponent_div_18_Template(rf, ctx) {
  if (rf & 1) {
    i0.\u0275\u0275elementStart(0, "div", 16);
    i0.\u0275\u0275element(1, "canvas", 17);
    i0.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    const ctx_r1 = i0.\u0275\u0275nextContext();
    i0.\u0275\u0275advance();
    i0.\u0275\u0275property("data", ctx_r1.chartData)("options", ctx_r1.chartOptions)("type", "scatter");
  }
}
Chart.register(zoomPlugin);
var DEFAULT_METRICS = ["Glucose", "Hemoglobin", "ALT", "AST", "Creatinine", "TSH"];
var normBandPlugin = {
  id: "normBand",
  beforeDatasetsDraw(chart, _args, options) {
    const ranges = options?.ranges ?? [];
    if (!ranges.length) {
      return;
    }
    const meta = chart.getDatasetMeta(0);
    if (!meta?.data?.length) {
      return;
    }
    const { ctx, scales, chartArea } = chart;
    const yScale = scales["y"];
    const xScale = scales["x"];
    if (!yScale || !xScale || !chartArea) {
      return;
    }
    const validRefs = ranges.filter((point) => point?.refMin !== null && point?.refMin !== void 0 && point?.refMax !== null && point?.refMax !== void 0).map((point) => ({ refMin: point.refMin, refMax: point.refMax }));
    if (!validRefs.length) {
      return;
    }
    const globalRefMin = validRefs[0].refMin;
    const globalRefMax = validRefs[0].refMax;
    ctx.save();
    ctx.strokeStyle = "rgba(118, 168, 255, 0.85)";
    ctx.setLineDash([8, 4]);
    ctx.lineWidth = 2;
    const yMin = yScale.getPixelForValue(globalRefMin);
    if (Number.isFinite(yMin)) {
      ctx.beginPath();
      ctx.moveTo(chartArea.left, yMin);
      ctx.lineTo(chartArea.right, yMin);
      ctx.stroke();
    }
    const yMax = yScale.getPixelForValue(globalRefMax);
    if (Number.isFinite(yMax)) {
      ctx.beginPath();
      ctx.moveTo(chartArea.left, yMax);
      ctx.lineTo(chartArea.right, yMax);
      ctx.stroke();
    }
    ctx.restore();
    const segments = meta.data.map((element, index) => {
      const point = ranges[index];
      if (!point || point.refMin === null || point.refMax === null || point.refMin === void 0 || point.refMax === void 0) {
        return null;
      }
      const pointElement = element;
      const x = pointElement.x;
      const yMinPix = yScale.getPixelForValue(point.refMin);
      const yMaxPix = yScale.getPixelForValue(point.refMax);
      if (!Number.isFinite(x) || !Number.isFinite(yMinPix) || !Number.isFinite(yMaxPix)) {
        return null;
      }
      return { x, yMin: yMinPix, yMax: yMaxPix };
    }).filter((seg) => seg !== null);
    if (segments.length) {
      ctx.save();
      ctx.beginPath();
      ctx.fillStyle = options?.fillStyle ?? "rgba(118, 168, 255, 0.08)";
      ctx.moveTo(segments[0].x, segments[0].yMax);
      segments.forEach((seg) => ctx.lineTo(seg.x, seg.yMax));
      for (let i = segments.length - 1; i >= 0; i--) {
        const seg = segments[i];
        ctx.lineTo(seg.x, seg.yMin);
      }
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }
  }
};
if (!Chart.registry?.getPlugin("normBand")) {
  Chart.register(normBandPlugin);
}
var DoctorPatientDetailPageComponent = class _DoctorPatientDetailPageComponent {
  doctorService = inject(DoctorService);
  route = inject(ActivatedRoute);
  chart;
  patientId = "";
  metricOptions = DEFAULT_METRICS;
  selectedMetric = this.metricOptions[0];
  loading = true;
  series = [];
  errorMessage = "";
  sub;
  chartData = { labels: [], datasets: [] };
  chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: "time",
        time: { unit: "day" },
        title: { display: true, text: "Date" },
        ticks: { color: "rgba(232, 236, 248, 0.55)" },
        grid: { color: "rgba(232, 236, 248, 0.06)", lineWidth: 0.5 }
      },
      y: {
        title: {
          display: false,
          // Will be updated dynamically with unit in updateChart()
          text: ""
        },
        ticks: { color: "rgba(232, 236, 248, 0.55)" },
        grid: { color: "rgba(232, 236, 248, 0.05)", lineWidth: 0.5 }
      }
    },
    plugins: {
      zoom: {
        pan: {
          enabled: true,
          mode: "xy"
          // Allow panning on both X and Y axes
        },
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: "xy"
          // Allow zooming on both X and Y axes
        }
      },
      normBand: {
        ranges: [],
        fillStyle: "rgba(118, 168, 255, 0.08)"
      }
      // Custom plugin type
    }
  };
  ngOnInit() {
    this.sub = this.route.paramMap.subscribe((params) => {
      this.patientId = params.get("id") ?? "";
      if (this.patientId) {
        this.loadSeries();
      }
    });
  }
  ngOnDestroy() {
    this.sub?.unsubscribe();
  }
  onMetricChange(metric) {
    if (this.selectedMetric === metric) {
      return;
    }
    this.selectedMetric = metric;
    this.loadSeries();
  }
  loadSeries() {
    if (!this.patientId || !this.selectedMetric) {
      return;
    }
    this.loading = true;
    this.errorMessage = "";
    this.doctorService.getSeries(this.patientId, this.selectedMetric).subscribe({
      next: (series) => {
        this.series = series;
        this.updateChart();
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? "Failed to load time series.";
        this.loading = false;
      }
    });
  }
  calculateYAxisMin(ranges) {
    if (!ranges.length)
      return void 0;
    const values = ranges.map((p) => p.y).filter((v) => v != null);
    const refMins = ranges.map((p) => p.refMin).filter((v) => v != null);
    if (!values.length)
      return void 0;
    const dataMin = Math.min(...values);
    const refMin = refMins.length ? Math.min(...refMins) : null;
    const minValue = refMin != null ? Math.min(dataMin, refMin) : dataMin;
    return minValue * 0.9;
  }
  calculateYAxisMax(ranges) {
    if (!ranges.length)
      return void 0;
    const values = ranges.map((p) => p.y).filter((v) => v != null);
    const refMaxs = ranges.map((p) => p.refMax).filter((v) => v != null);
    if (!values.length)
      return void 0;
    const dataMax = Math.max(...values);
    const refMax = refMaxs.length ? Math.max(...refMaxs) : null;
    const maxValue = refMax != null ? Math.max(dataMax, refMax) : dataMax;
    return maxValue * 1.1;
  }
  updateChart() {
    const labels = this.series.map((point) => point.t);
    const data = this.series.map((point) => point.y);
    const unit = this.series.length > 0 && this.series[0]?.unit ? this.series[0].unit : null;
    const yAxisTitle = unit || "";
    this.chartData = {
      labels,
      datasets: [
        {
          label: this.selectedMetric,
          data,
          borderColor: "#76a8ff",
          backgroundColor: "rgba(118, 168, 255, 0.25)",
          tension: 0.25,
          fill: false
        }
      ]
    };
    if (this.chartOptions?.scales?.["y"]) {
      const yScale = this.chartOptions.scales["y"];
      if (yScale) {
        yScale.title = {
          display: !!yAxisTitle,
          text: yAxisTitle,
          color: "rgba(232, 236, 248, 0.75)",
          font: {
            size: 12,
            family: "Inter, system-ui, sans-serif",
            weight: 500
          },
          padding: { top: 0, bottom: 8 }
        };
        yScale.min = this.calculateYAxisMin(this.series);
        yScale.max = this.calculateYAxisMax(this.series);
      }
    }
    const plugins = this.chartOptions?.plugins;
    if (plugins?.normBand) {
      plugins.normBand.ranges = this.series;
    }
    const validRefs = this.series.filter((p) => p.refMin != null && p.refMax != null);
    if (validRefs.length > 0) {
      console.log("[Chart] Reference values found:", {
        count: validRefs.length,
        refMin: validRefs[0].refMin,
        refMax: validRefs[0].refMax,
        yAxisMin: this.calculateYAxisMin(this.series),
        yAxisMax: this.calculateYAxisMax(this.series)
      });
    } else {
      console.log("[Chart] No reference values found in series:", this.series);
    }
    this.chart?.update();
  }
  static \u0275fac = function DoctorPatientDetailPageComponent_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _DoctorPatientDetailPageComponent)();
  };
  static \u0275cmp = /* @__PURE__ */ i0.\u0275\u0275defineComponent({ type: _DoctorPatientDetailPageComponent, selectors: [["app-doctor-patient-detail-page"]], viewQuery: function DoctorPatientDetailPageComponent_Query(rf, ctx) {
    if (rf & 1) {
      i0.\u0275\u0275viewQuery(BaseChartDirective, 5);
    }
    if (rf & 2) {
      let _t;
      i0.\u0275\u0275queryRefresh(_t = i0.\u0275\u0275loadQuery()) && (ctx.chart = _t.first);
    }
  }, standalone: false, decls: 19, vars: 16, consts: [[1, "space-y-6"], [3, "extraClass"], [1, "flex", "flex-col", "lg:flex-row", "lg:items-end", "lg:justify-between", "gap-4"], [1, "text-2xl", "font-semibold", "text-[var(--text)]"], [1, "text-sm", "text-[var(--text-dim)]"], [1, "flex", "flex-wrap", "items-center", "gap-2"], [1, "text-xs", "uppercase", "tracking-[0.2em]", "text-[var(--text-dim)]"], [1, "input-glass", "min-w-[200px]", 3, "ngModelChange", "ngModel"], [3, "ngValue", 4, "ngFor", "ngForOf"], ["class", "flex flex-col items-center justify-center gap-3 py-10 text-[var(--text-dim)]", 4, "ngIf"], ["class", "glass glass-strong text-[var(--danger)] p-4", 4, "ngIf"], ["class", "h-[260px] sm:h-[340px]", 4, "ngIf"], [3, "ngValue"], [1, "flex", "flex-col", "items-center", "justify-center", "gap-3", "py-10", "text-[var(--text-dim)]"], [1, "animate-spin", "h-10", "w-10", "border-2", "border-[var(--accent)]", "border-t-transparent", "rounded-full"], [1, "glass", "glass-strong", "text-[var(--danger)]", "p-4"], [1, "h-[260px]", "sm:h-[340px]"], ["baseChart", "", 3, "data", "options", "type"]], template: function DoctorPatientDetailPageComponent_Template(rf, ctx) {
    if (rf & 1) {
      i0.\u0275\u0275elementStart(0, "div", 0)(1, "app-glass-card", 1)(2, "div", 2)(3, "div")(4, "h2", 3);
      i0.\u0275\u0275text(5);
      i0.\u0275\u0275pipe(6, "translate");
      i0.\u0275\u0275elementEnd();
      i0.\u0275\u0275elementStart(7, "p", 4);
      i0.\u0275\u0275text(8);
      i0.\u0275\u0275pipe(9, "translate");
      i0.\u0275\u0275elementEnd()();
      i0.\u0275\u0275elementStart(10, "div", 5)(11, "span", 6);
      i0.\u0275\u0275text(12);
      i0.\u0275\u0275pipe(13, "translate");
      i0.\u0275\u0275elementEnd();
      i0.\u0275\u0275elementStart(14, "select", 7);
      i0.\u0275\u0275listener("ngModelChange", function DoctorPatientDetailPageComponent_Template_select_ngModelChange_14_listener($event) {
        return ctx.onMetricChange($event);
      });
      i0.\u0275\u0275template(15, DoctorPatientDetailPageComponent_option_15_Template, 2, 2, "option", 8);
      i0.\u0275\u0275elementEnd()()();
      i0.\u0275\u0275template(16, DoctorPatientDetailPageComponent_div_16_Template, 4, 3, "div", 9)(17, DoctorPatientDetailPageComponent_div_17_Template, 2, 1, "div", 10)(18, DoctorPatientDetailPageComponent_div_18_Template, 2, 3, "div", 11);
      i0.\u0275\u0275elementEnd()();
    }
    if (rf & 2) {
      i0.\u0275\u0275advance();
      i0.\u0275\u0275property("extraClass", "glass-strong space-y-5");
      i0.\u0275\u0275advance(4);
      i0.\u0275\u0275textInterpolate2("", i0.\u0275\u0275pipeBind1(6, 10, "doctor.detailTitle"), " ", ctx.patientId);
      i0.\u0275\u0275advance(3);
      i0.\u0275\u0275textInterpolate(i0.\u0275\u0275pipeBind1(9, 12, "doctor.detailSubtitle"));
      i0.\u0275\u0275advance(4);
      i0.\u0275\u0275textInterpolate(i0.\u0275\u0275pipeBind1(13, 14, "doctor.metric"));
      i0.\u0275\u0275advance(2);
      i0.\u0275\u0275property("ngModel", ctx.selectedMetric);
      i0.\u0275\u0275advance();
      i0.\u0275\u0275property("ngForOf", ctx.metricOptions);
      i0.\u0275\u0275advance();
      i0.\u0275\u0275property("ngIf", ctx.loading);
      i0.\u0275\u0275advance();
      i0.\u0275\u0275property("ngIf", !ctx.loading && ctx.errorMessage);
      i0.\u0275\u0275advance();
      i0.\u0275\u0275property("ngIf", !ctx.loading && !ctx.errorMessage);
    }
  }, styles: ["\n\n[_nghost-%COMP%] {\n  display: block;\n}\nselect[_ngcontent-%COMP%] {\n  min-width: 200px;\n}\n/*# sourceMappingURL=doctor-patient-detail-page.component.css.map */"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i0.\u0275setClassMetadata(DoctorPatientDetailPageComponent, [{
    type: Component,
    args: [{ selector: "app-doctor-patient-detail-page", standalone: false, template: `<div class="space-y-6">
  <app-glass-card [extraClass]="'glass-strong space-y-5'">
    <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
      <div>
        <h2 class="text-2xl font-semibold text-[var(--text)]">{{ 'doctor.detailTitle' | translate }} {{ patientId }}</h2>
        <p class="text-sm text-[var(--text-dim)]">{{ 'doctor.detailSubtitle' | translate }}</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs uppercase tracking-[0.2em] text-[var(--text-dim)]">{{ 'doctor.metric' | translate }}</span>
        <select class="input-glass min-w-[200px]" [ngModel]="selectedMetric" (ngModelChange)="onMetricChange($event)">
          <option *ngFor="let option of metricOptions" [ngValue]="option">{{ option }}</option>
        </select>
      </div>
    </div>

    <div *ngIf="loading" class="flex flex-col items-center justify-center gap-3 py-10 text-[var(--text-dim)]">
      <div class="animate-spin h-10 w-10 border-2 border-[var(--accent)] border-t-transparent rounded-full"></div>
      {{ 'doctor.loading' | translate }}
    </div>

    <div *ngIf="!loading && errorMessage" class="glass glass-strong text-[var(--danger)] p-4">
      {{ errorMessage }}
    </div>

    <div class="h-[260px] sm:h-[340px]" *ngIf="!loading && !errorMessage">
      <canvas baseChart [data]="chartData" [options]="chartOptions" [type]="'scatter'"></canvas>
    </div>
  </app-glass-card>
</div>
`, styles: ["/* src/app/features/doctor/pages/patient-detail/doctor-patient-detail-page.component.scss */\n:host {\n  display: block;\n}\nselect {\n  min-width: 200px;\n}\n/*# sourceMappingURL=doctor-patient-detail-page.component.css.map */\n"] }]
  }], null, { chart: [{
    type: ViewChild,
    args: [BaseChartDirective]
  }] });
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i0.\u0275setClassDebugInfo(DoctorPatientDetailPageComponent, { className: "DoctorPatientDetailPageComponent", filePath: "src/app/features/doctor/pages/patient-detail/doctor-patient-detail-page.component.ts", lineNumber: 135 });
})();
(() => {
  const id = "src%2Fapp%2Ffeatures%2Fdoctor%2Fpages%2Fpatient-detail%2Fdoctor-patient-detail-page.component.ts%40DoctorPatientDetailPageComponent";
  function DoctorPatientDetailPageComponent_HmrLoad(t) {
    import(
      /* @vite-ignore */
      __vite__injectQuery(i0.\u0275\u0275getReplaceMetadataURL(id, t, import.meta.url), 'import')
    ).then((m) => m.default && i0.\u0275\u0275replaceMetadata(DoctorPatientDetailPageComponent, m.default, [i0], [BaseChartDirective, Component, ViewChild], import.meta, id));
  }
  (typeof ngDevMode === "undefined" || ngDevMode) && DoctorPatientDetailPageComponent_HmrLoad(Date.now());
  (typeof ngDevMode === "undefined" || ngDevMode) && (import.meta.hot && import.meta.hot.on("angular:component-update", (d) => d.id === id && DoctorPatientDetailPageComponent_HmrLoad(d.timestamp)));
})();

// src/app/features/doctor/pages/patients/doctor-patients-page.component.ts
function DoctorPatientsPageComponent_div_13_Template(rf, ctx) {
  if (rf & 1) {
    i02.\u0275\u0275elementStart(0, "div", 10);
    i02.\u0275\u0275element(1, "div", 11);
    i02.\u0275\u0275text(2);
    i02.\u0275\u0275pipe(3, "translate");
    i02.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    i02.\u0275\u0275advance(2);
    i02.\u0275\u0275textInterpolate1(" ", i02.\u0275\u0275pipeBind1(3, 1, "doctor.patientsLoading"), " ");
  }
}
function DoctorPatientsPageComponent_div_14_Template(rf, ctx) {
  if (rf & 1) {
    i02.\u0275\u0275elementStart(0, "div", 12);
    i02.\u0275\u0275text(1);
    i02.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    const ctx_r0 = i02.\u0275\u0275nextContext();
    i02.\u0275\u0275advance();
    i02.\u0275\u0275textInterpolate1(" ", ctx_r0.errorMessage, " ");
  }
}
function DoctorPatientsPageComponent_div_15_Template(rf, ctx) {
  if (rf & 1) {
    i02.\u0275\u0275elementStart(0, "div", 4);
    i02.\u0275\u0275text(1);
    i02.\u0275\u0275pipe(2, "translate");
    i02.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    i02.\u0275\u0275advance();
    i02.\u0275\u0275textInterpolate1(" ", i02.\u0275\u0275pipeBind1(2, 1, "doctor.patientsEmpty"), " ");
  }
}
function DoctorPatientsPageComponent_div_16_button_1_Template(rf, ctx) {
  if (rf & 1) {
    const _r2 = i02.\u0275\u0275getCurrentView();
    i02.\u0275\u0275elementStart(0, "button", 15);
    i02.\u0275\u0275listener("click", function DoctorPatientsPageComponent_div_16_button_1_Template_button_click_0_listener() {
      const patient_r3 = i02.\u0275\u0275restoreView(_r2).$implicit;
      const ctx_r0 = i02.\u0275\u0275nextContext(2);
      return i02.\u0275\u0275resetView(ctx_r0.openPatient(patient_r3));
    });
    i02.\u0275\u0275elementStart(1, "div")(2, "p", 16);
    i02.\u0275\u0275text(3);
    i02.\u0275\u0275elementEnd();
    i02.\u0275\u0275elementStart(4, "p", 17);
    i02.\u0275\u0275text(5);
    i02.\u0275\u0275pipe(6, "translate");
    i02.\u0275\u0275pipe(7, "date");
    i02.\u0275\u0275elementEnd()();
    i02.\u0275\u0275elementStart(8, "span", 18);
    i02.\u0275\u0275text(9);
    i02.\u0275\u0275pipe(10, "translate");
    i02.\u0275\u0275pipe(11, "date");
    i02.\u0275\u0275elementEnd()();
  }
  if (rf & 2) {
    const patient_r3 = ctx.$implicit;
    i02.\u0275\u0275advance(3);
    i02.\u0275\u0275textInterpolate(patient_r3.email);
    i02.\u0275\u0275advance(2);
    i02.\u0275\u0275textInterpolate2("", i02.\u0275\u0275pipeBind1(6, 5, "doctor.grantedAt"), " ", i02.\u0275\u0275pipeBind2(7, 7, patient_r3.granted_at, "d MMMM yyyy, HH:mm"));
    i02.\u0275\u0275advance(4);
    i02.\u0275\u0275textInterpolate2(" ", i02.\u0275\u0275pipeBind1(10, 10, "doctor.latestAnalysis"), " ", patient_r3.latest_taken_at ? i02.\u0275\u0275pipeBind2(11, 12, patient_r3.latest_taken_at, "d MMM yyyy") : "-", " ");
  }
}
function DoctorPatientsPageComponent_div_16_Template(rf, ctx) {
  if (rf & 1) {
    i02.\u0275\u0275elementStart(0, "div", 13);
    i02.\u0275\u0275template(1, DoctorPatientsPageComponent_div_16_button_1_Template, 12, 15, "button", 14);
    i02.\u0275\u0275elementEnd();
  }
  if (rf & 2) {
    const ctx_r0 = i02.\u0275\u0275nextContext();
    i02.\u0275\u0275advance();
    i02.\u0275\u0275property("ngForOf", ctx_r0.patients);
  }
}
var DoctorPatientsPageComponent = class _DoctorPatientsPageComponent {
  doctorService = inject2(DoctorService);
  router = inject2(Router);
  loading = true;
  patients = [];
  errorMessage = "";
  ngOnInit() {
    this.doctorService.listPatients().subscribe({
      next: (response) => {
        this.patients = response?.patients ?? [];
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? "Failed to load patients list.";
        this.loading = false;
      }
    });
  }
  openPatient(patient) {
    void this.router.navigate(["/doctor/patient", patient.patient_id]);
  }
  static \u0275fac = function DoctorPatientsPageComponent_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _DoctorPatientsPageComponent)();
  };
  static \u0275cmp = /* @__PURE__ */ i02.\u0275\u0275defineComponent({ type: _DoctorPatientsPageComponent, selectors: [["app-doctor-patients-page"]], standalone: false, decls: 17, vars: 15, consts: [[1, "space-y-6"], [3, "extraClass"], [1, "flex", "items-center", "justify-between", "gap-3", "flex-wrap"], [1, "text-2xl", "font-semibold", "text-[var(--text)]"], [1, "text-sm", "text-[var(--text-dim)]"], [1, "badge-glass"], ["class", "flex flex-col items-center justify-center gap-3 py-10 text-[var(--text-dim)]", 4, "ngIf"], ["class", "glass glass-strong text-[var(--danger)] p-4", 4, "ngIf"], ["class", "text-sm text-[var(--text-dim)]", 4, "ngIf"], ["class", "flex flex-col gap-3", 4, "ngIf"], [1, "flex", "flex-col", "items-center", "justify-center", "gap-3", "py-10", "text-[var(--text-dim)]"], [1, "animate-spin", "h-10", "w-10", "border-2", "border-[var(--accent)]", "border-t-transparent", "rounded-full"], [1, "glass", "glass-strong", "text-[var(--danger)]", "p-4"], [1, "flex", "flex-col", "gap-3"], ["type", "button", "class", "glass glass-strong flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-4 text-left rounded-[var(--r-lg)] transition-transform", 3, "click", 4, "ngFor", "ngForOf"], ["type", "button", 1, "glass", "glass-strong", "flex", "flex-col", "sm:flex-row", "sm:items-center", "sm:justify-between", "gap-2", "p-4", "text-left", "rounded-[var(--r-lg)]", "transition-transform", 3, "click"], [1, "text-sm", "font-semibold", "text-[var(--text)]"], [1, "text-xs", "text-[var(--text-dim)]"], [1, "badge-glass", "badge-accent"]], template: function DoctorPatientsPageComponent_Template(rf, ctx) {
    if (rf & 1) {
      i02.\u0275\u0275elementStart(0, "div", 0)(1, "app-glass-card", 1)(2, "div", 2)(3, "div")(4, "h2", 3);
      i02.\u0275\u0275text(5);
      i02.\u0275\u0275pipe(6, "translate");
      i02.\u0275\u0275elementEnd();
      i02.\u0275\u0275elementStart(7, "p", 4);
      i02.\u0275\u0275text(8);
      i02.\u0275\u0275pipe(9, "translate");
      i02.\u0275\u0275elementEnd()();
      i02.\u0275\u0275elementStart(10, "span", 5);
      i02.\u0275\u0275text(11);
      i02.\u0275\u0275pipe(12, "translate");
      i02.\u0275\u0275elementEnd()();
      i02.\u0275\u0275template(13, DoctorPatientsPageComponent_div_13_Template, 4, 3, "div", 6)(14, DoctorPatientsPageComponent_div_14_Template, 2, 1, "div", 7)(15, DoctorPatientsPageComponent_div_15_Template, 3, 3, "div", 8)(16, DoctorPatientsPageComponent_div_16_Template, 2, 1, "div", 9);
      i02.\u0275\u0275elementEnd()();
    }
    if (rf & 2) {
      i02.\u0275\u0275advance();
      i02.\u0275\u0275property("extraClass", "glass-strong space-y-4");
      i02.\u0275\u0275advance(4);
      i02.\u0275\u0275textInterpolate(i02.\u0275\u0275pipeBind1(6, 9, "doctor.patientsTitle"));
      i02.\u0275\u0275advance(3);
      i02.\u0275\u0275textInterpolate(i02.\u0275\u0275pipeBind1(9, 11, "doctor.patientsSubtitle"));
      i02.\u0275\u0275advance(3);
      i02.\u0275\u0275textInterpolate2("", ctx.patients.length, " ", i02.\u0275\u0275pipeBind1(12, 13, "doctor.patientsTitle"));
      i02.\u0275\u0275advance(2);
      i02.\u0275\u0275property("ngIf", ctx.loading);
      i02.\u0275\u0275advance();
      i02.\u0275\u0275property("ngIf", !ctx.loading && ctx.errorMessage);
      i02.\u0275\u0275advance();
      i02.\u0275\u0275property("ngIf", !ctx.loading && !ctx.errorMessage && ctx.patients.length === 0);
      i02.\u0275\u0275advance();
      i02.\u0275\u0275property("ngIf", !ctx.loading && ctx.patients.length);
    }
  }, dependencies: [i1.NgClass, i1.NgComponentOutlet, i1.NgForOf, i1.NgIf, i1.NgTemplateOutlet, i1.NgStyle, i1.NgSwitch, i1.NgSwitchCase, i1.NgSwitchDefault, i1.NgPlural, i1.NgPluralCase, i2.\u0275NgNoValidate, i2.NgSelectOption, i2.\u0275NgSelectMultipleOption, i2.DefaultValueAccessor, i2.NumberValueAccessor, i2.RangeValueAccessor, i2.CheckboxControlValueAccessor, i2.SelectControlValueAccessor, i2.SelectMultipleControlValueAccessor, i2.RadioControlValueAccessor, i2.NgControlStatus, i2.NgControlStatusGroup, i2.RequiredValidator, i2.MinLengthValidator, i2.MaxLengthValidator, i2.PatternValidator, i2.CheckboxRequiredValidator, i2.EmailValidator, i2.MinValidator, i2.MaxValidator, i2.NgModel, i2.NgModelGroup, i2.NgForm, i2.FormControlDirective, i2.FormGroupDirective, i2.FormControlName, i2.FormGroupName, i2.FormArrayName, i3.RouterOutlet, i3.RouterLink, i3.RouterLinkActive, i3.\u0275EmptyOutletComponent, i4.NgbAccordionButton, i4.NgbAccordionDirective, i4.NgbAccordionItem, i4.NgbAccordionHeader, i4.NgbAccordionToggle, i4.NgbAccordionBody, i4.NgbAccordionCollapse, i4.NgbAlert, i4.NgbCarousel, i4.NgbSlide, i4.NgbCollapse, i4.NgbDatepicker, i4.NgbDatepickerContent, i4.NgbInputDatepicker, i4.NgbDatepickerMonth, i4.NgbDropdown, i4.NgbDropdownAnchor, i4.NgbDropdownToggle, i4.NgbDropdownMenu, i4.NgbDropdownItem, i4.NgbDropdownButtonItem, i4.NgbNavContent, i4.NgbNav, i4.NgbNavItem, i4.NgbNavItemRole, i4.NgbNavLink, i4.NgbNavLinkButton, i4.NgbNavLinkBase, i4.NgbNavOutlet, i4.NgbNavPane, i4.NgbPagination, i4.NgbPaginationEllipsis, i4.NgbPaginationFirst, i4.NgbPaginationLast, i4.NgbPaginationNext, i4.NgbPaginationNumber, i4.NgbPaginationPrevious, i4.NgbPaginationPages, i4.NgbPopover, i4.NgbProgressbar, i4.NgbProgressbarStacked, i4.NgbRating, i4.NgbScrollSpy, i4.NgbScrollSpyItem, i4.NgbScrollSpyFragment, i4.NgbScrollSpyMenu, i4.NgbTimepicker, i4.NgbToast, i4.NgbToastHeader, i4.NgbTooltip, i4.NgbHighlight, i4.NgbTypeahead, i5.TranslateDirective, i6.BaseChartDirective, PatientTabBarComponent, GlassCardComponent, GlassButtonDirective, GlassInputComponent, GlassToolbarComponent, GlassTabbarComponent, DoctorPatientDetailPageComponent, i1.AsyncPipe, i1.UpperCasePipe, i1.LowerCasePipe, i1.JsonPipe, i1.SlicePipe, i1.DecimalPipe, i1.PercentPipe, i1.TitleCasePipe, i1.CurrencyPipe, i1.DatePipe, i1.I18nPluralPipe, i1.I18nSelectPipe, i1.KeyValuePipe, i5.TranslatePipe], styles: ["\n\n[_nghost-%COMP%] {\n  display: block;\n}\nbutton[_ngcontent-%COMP%]:hover {\n  transform: translateY(-2px);\n}\n/*# sourceMappingURL=doctor-patients-page.component.css.map */"] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i02.\u0275setClassMetadata(DoctorPatientsPageComponent, [{
    type: Component2,
    args: [{ selector: "app-doctor-patients-page", standalone: false, template: `<div class="space-y-6">
  <app-glass-card [extraClass]="'glass-strong space-y-4'">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <h2 class="text-2xl font-semibold text-[var(--text)]">{{ 'doctor.patientsTitle' | translate }}</h2>
        <p class="text-sm text-[var(--text-dim)]">{{ 'doctor.patientsSubtitle' | translate }}</p>
      </div>
      <span class="badge-glass">{{ patients.length }} {{ 'doctor.patientsTitle' | translate }}</span>
    </div>

    <div *ngIf="loading" class="flex flex-col items-center justify-center gap-3 py-10 text-[var(--text-dim)]">
      <div class="animate-spin h-10 w-10 border-2 border-[var(--accent)] border-t-transparent rounded-full"></div>
      {{ 'doctor.patientsLoading' | translate }}
    </div>

    <div *ngIf="!loading && errorMessage" class="glass glass-strong text-[var(--danger)] p-4">
      {{ errorMessage }}
    </div>

    <div *ngIf="!loading && !errorMessage && patients.length === 0" class="text-sm text-[var(--text-dim)]">
      {{ 'doctor.patientsEmpty' | translate }}
    </div>

    <div class="flex flex-col gap-3" *ngIf="!loading && patients.length">
      <button
        type="button"
        class="glass glass-strong flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-4 text-left rounded-[var(--r-lg)] transition-transform"
        *ngFor="let patient of patients"
        (click)="openPatient(patient)"
      >
        <div>
          <p class="text-sm font-semibold text-[var(--text)]">{{ patient.email }}</p>
          <p class="text-xs text-[var(--text-dim)]">{{ 'doctor.grantedAt' | translate }} {{ patient.granted_at | date: 'd MMMM yyyy, HH:mm' }}</p>
        </div>
        <span class="badge-glass badge-accent">
          {{ 'doctor.latestAnalysis' | translate }} {{ patient.latest_taken_at ? (patient.latest_taken_at | date: 'd MMM yyyy') : '-' }}
        </span>
      </button>
    </div>
  </app-glass-card>
</div>
`, styles: ["/* src/app/features/doctor/pages/patients/doctor-patients-page.component.scss */\n:host {\n  display: block;\n}\nbutton:hover {\n  transform: translateY(-2px);\n}\n/*# sourceMappingURL=doctor-patients-page.component.css.map */\n"] }]
  }], null, null);
})();
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i02.\u0275setClassDebugInfo(DoctorPatientsPageComponent, { className: "DoctorPatientsPageComponent", filePath: "src/app/features/doctor/pages/patients/doctor-patients-page.component.ts", lineNumber: 13 });
})();
(() => {
  const id = "src%2Fapp%2Ffeatures%2Fdoctor%2Fpages%2Fpatients%2Fdoctor-patients-page.component.ts%40DoctorPatientsPageComponent";
  function DoctorPatientsPageComponent_HmrLoad(t) {
    import(
      /* @vite-ignore */
      __vite__injectQuery(i02.\u0275\u0275getReplaceMetadataURL(id, t, import.meta.url), 'import')
    ).then((m) => m.default && i02.\u0275\u0275replaceMetadata(DoctorPatientsPageComponent, m.default, [i02, i1, i2, i3, i4, i5, i6, patient_tab_bar_component_exports, glass_card_component_exports, glass_button_directive_exports, glass_input_component_exports, glass_toolbar_component_exports, glass_tabbar_component_exports, doctor_patient_detail_page_component_exports], [Component2], import.meta, id));
  }
  (typeof ngDevMode === "undefined" || ngDevMode) && DoctorPatientsPageComponent_HmrLoad(Date.now());
  (typeof ngDevMode === "undefined" || ngDevMode) && (import.meta.hot && import.meta.hot.on("angular:component-update", (d) => d.id === id && DoctorPatientsPageComponent_HmrLoad(d.timestamp)));
})();

// src/app/features/doctor/doctor-routing.module.ts
import * as i03 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import * as i12 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
var routes = [
  {
    path: "",
    component: DoctorPatientsPageComponent,
    data: {
      title: "Doctor workspace",
      subtitle: "Patients who shared their labs with you",
      accent: "doctor"
    }
  },
  {
    path: "patient/:id",
    component: DoctorPatientDetailPageComponent,
    data: {
      title: "Patient card",
      subtitle: "Charts and metrics for the selected period",
      accent: "doctor",
      showBack: true,
      back: "/doctor"
    }
  }
];
var DoctorRoutingModule = class _DoctorRoutingModule {
  static \u0275fac = function DoctorRoutingModule_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _DoctorRoutingModule)();
  };
  static \u0275mod = /* @__PURE__ */ i03.\u0275\u0275defineNgModule({ type: _DoctorRoutingModule });
  static \u0275inj = /* @__PURE__ */ i03.\u0275\u0275defineInjector({ imports: [RouterModule.forChild(routes), RouterModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i03.\u0275setClassMetadata(DoctorRoutingModule, [{
    type: NgModule,
    args: [{
      imports: [RouterModule.forChild(routes)],
      exports: [RouterModule]
    }]
  }], null, null);
})();

// src/app/features/doctor/doctor.module.ts
import * as i04 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_core.js?v=24701eb5";
import * as i13 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_common.js?v=24701eb5";
import * as i22 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_forms.js?v=24701eb5";
import * as i32 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@angular_router.js?v=24701eb5";
import * as i42 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@ng-bootstrap_ng-bootstrap.js?v=24701eb5";
import * as i52 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/@ngx-translate_core.js?v=24701eb5";
import * as i62 from "/@fs/C:/Users/jolypab/Documents/CODE/medic/frontend/.angular/cache/20.3.7/medic-frontend/vite/deps/ng2-charts.js?v=24701eb5";
var DoctorModule = class _DoctorModule {
  static \u0275fac = function DoctorModule_Factory(__ngFactoryType__) {
    return new (__ngFactoryType__ || _DoctorModule)();
  };
  static \u0275mod = /* @__PURE__ */ i04.\u0275\u0275defineNgModule({ type: _DoctorModule });
  static \u0275inj = /* @__PURE__ */ i04.\u0275\u0275defineInjector({ imports: [SharedModule, DoctorRoutingModule] });
};
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && i04.\u0275setClassMetadata(DoctorModule, [{
    type: NgModule2,
    args: [{
      declarations: [DoctorPatientsPageComponent, DoctorPatientDetailPageComponent],
      imports: [SharedModule, DoctorRoutingModule]
    }]
  }], null, null);
})();
i04.\u0275\u0275setComponentScope(DoctorPatientDetailPageComponent, [i13.NgClass, i13.NgComponentOutlet, i13.NgForOf, i13.NgIf, i13.NgTemplateOutlet, i13.NgStyle, i13.NgSwitch, i13.NgSwitchCase, i13.NgSwitchDefault, i13.NgPlural, i13.NgPluralCase, i22.\u0275NgNoValidate, i22.NgSelectOption, i22.\u0275NgSelectMultipleOption, i22.DefaultValueAccessor, i22.NumberValueAccessor, i22.RangeValueAccessor, i22.CheckboxControlValueAccessor, i22.SelectControlValueAccessor, i22.SelectMultipleControlValueAccessor, i22.RadioControlValueAccessor, i22.NgControlStatus, i22.NgControlStatusGroup, i22.RequiredValidator, i22.MinLengthValidator, i22.MaxLengthValidator, i22.PatternValidator, i22.CheckboxRequiredValidator, i22.EmailValidator, i22.MinValidator, i22.MaxValidator, i22.NgModel, i22.NgModelGroup, i22.NgForm, i22.FormControlDirective, i22.FormGroupDirective, i22.FormControlName, i22.FormGroupName, i22.FormArrayName, i32.RouterOutlet, i32.RouterLink, i32.RouterLinkActive, i32.\u0275EmptyOutletComponent, i42.NgbAccordionButton, i42.NgbAccordionDirective, i42.NgbAccordionItem, i42.NgbAccordionHeader, i42.NgbAccordionToggle, i42.NgbAccordionBody, i42.NgbAccordionCollapse, i42.NgbAlert, i42.NgbCarousel, i42.NgbSlide, i42.NgbCollapse, i42.NgbDatepicker, i42.NgbDatepickerContent, i42.NgbInputDatepicker, i42.NgbDatepickerMonth, i42.NgbDropdown, i42.NgbDropdownAnchor, i42.NgbDropdownToggle, i42.NgbDropdownMenu, i42.NgbDropdownItem, i42.NgbDropdownButtonItem, i42.NgbNavContent, i42.NgbNav, i42.NgbNavItem, i42.NgbNavItemRole, i42.NgbNavLink, i42.NgbNavLinkButton, i42.NgbNavLinkBase, i42.NgbNavOutlet, i42.NgbNavPane, i42.NgbPagination, i42.NgbPaginationEllipsis, i42.NgbPaginationFirst, i42.NgbPaginationLast, i42.NgbPaginationNext, i42.NgbPaginationNumber, i42.NgbPaginationPrevious, i42.NgbPaginationPages, i42.NgbPopover, i42.NgbProgressbar, i42.NgbProgressbarStacked, i42.NgbRating, i42.NgbScrollSpy, i42.NgbScrollSpyItem, i42.NgbScrollSpyFragment, i42.NgbScrollSpyMenu, i42.NgbTimepicker, i42.NgbToast, i42.NgbToastHeader, i42.NgbTooltip, i42.NgbHighlight, i42.NgbTypeahead, i52.TranslateDirective, i62.BaseChartDirective, PatientTabBarComponent, GlassCardComponent, GlassButtonDirective, GlassInputComponent, GlassToolbarComponent, GlassTabbarComponent, DoctorPatientsPageComponent], [i13.AsyncPipe, i13.UpperCasePipe, i13.LowerCasePipe, i13.JsonPipe, i13.SlicePipe, i13.DecimalPipe, i13.PercentPipe, i13.TitleCasePipe, i13.CurrencyPipe, i13.DatePipe, i13.I18nPluralPipe, i13.I18nSelectPipe, i13.KeyValuePipe, i52.TranslatePipe]);
export {
  DoctorModule
};


//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbInNyYy9hcHAvZmVhdHVyZXMvZG9jdG9yL2RvY3Rvci5tb2R1bGUudHMiLCJzcmMvYXBwL2ZlYXR1cmVzL2RvY3Rvci9kb2N0b3Itcm91dGluZy5tb2R1bGUudHMiLCJzcmMvYXBwL2ZlYXR1cmVzL2RvY3Rvci9wYWdlcy9wYXRpZW50cy9kb2N0b3ItcGF0aWVudHMtcGFnZS5jb21wb25lbnQudHMiLCJzcmMvYXBwL2ZlYXR1cmVzL2RvY3Rvci9wYWdlcy9wYXRpZW50cy9kb2N0b3ItcGF0aWVudHMtcGFnZS5jb21wb25lbnQuaHRtbCIsInNyYy9hcHAvZmVhdHVyZXMvZG9jdG9yL3BhZ2VzL3BhdGllbnQtZGV0YWlsL2RvY3Rvci1wYXRpZW50LWRldGFpbC1wYWdlLmNvbXBvbmVudC50cyIsInNyYy9hcHAvZmVhdHVyZXMvZG9jdG9yL3BhZ2VzL3BhdGllbnQtZGV0YWlsL2RvY3Rvci1wYXRpZW50LWRldGFpbC1wYWdlLmNvbXBvbmVudC5odG1sIl0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IE5nTW9kdWxlIH0gZnJvbSAnQGFuZ3VsYXIvY29yZSc7XG5cbmltcG9ydCB7IFNoYXJlZE1vZHVsZSB9IGZyb20gJy4uLy4uL3NoYXJlZC9zaGFyZWQubW9kdWxlJztcbmltcG9ydCB7IERvY3RvclJvdXRpbmdNb2R1bGUgfSBmcm9tICcuL2RvY3Rvci1yb3V0aW5nLm1vZHVsZSc7XG5pbXBvcnQgeyBEb2N0b3JQYXRpZW50c1BhZ2VDb21wb25lbnQgfSBmcm9tICcuL3BhZ2VzL3BhdGllbnRzL2RvY3Rvci1wYXRpZW50cy1wYWdlLmNvbXBvbmVudCc7XG5pbXBvcnQgeyBEb2N0b3JQYXRpZW50RGV0YWlsUGFnZUNvbXBvbmVudCB9IGZyb20gJy4vcGFnZXMvcGF0aWVudC1kZXRhaWwvZG9jdG9yLXBhdGllbnQtZGV0YWlsLXBhZ2UuY29tcG9uZW50JztcblxuQE5nTW9kdWxlKHtcbiAgZGVjbGFyYXRpb25zOiBbRG9jdG9yUGF0aWVudHNQYWdlQ29tcG9uZW50LCBEb2N0b3JQYXRpZW50RGV0YWlsUGFnZUNvbXBvbmVudF0sXG4gIGltcG9ydHM6IFtTaGFyZWRNb2R1bGUsIERvY3RvclJvdXRpbmdNb2R1bGVdLFxufSlcbmV4cG9ydCBjbGFzcyBEb2N0b3JNb2R1bGUge31cblxyXG4iLCJpbXBvcnQgeyBOZ01vZHVsZSB9IGZyb20gJ0Bhbmd1bGFyL2NvcmUnO1xuaW1wb3J0IHsgUm91dGVyTW9kdWxlLCBSb3V0ZXMgfSBmcm9tICdAYW5ndWxhci9yb3V0ZXInO1xuXG5pbXBvcnQgeyBEb2N0b3JQYXRpZW50c1BhZ2VDb21wb25lbnQgfSBmcm9tICcuL3BhZ2VzL3BhdGllbnRzL2RvY3Rvci1wYXRpZW50cy1wYWdlLmNvbXBvbmVudCc7XG5pbXBvcnQgeyBEb2N0b3JQYXRpZW50RGV0YWlsUGFnZUNvbXBvbmVudCB9IGZyb20gJy4vcGFnZXMvcGF0aWVudC1kZXRhaWwvZG9jdG9yLXBhdGllbnQtZGV0YWlsLXBhZ2UuY29tcG9uZW50JztcblxuY29uc3Qgcm91dGVzOiBSb3V0ZXMgPSBbXG4gIHtcbiAgICBwYXRoOiAnJyxcbiAgICBjb21wb25lbnQ6IERvY3RvclBhdGllbnRzUGFnZUNvbXBvbmVudCxcbiAgICBkYXRhOiB7XG4gICAgICB0aXRsZTogJ0RvY3RvciB3b3Jrc3BhY2UnLFxuICAgICAgc3VidGl0bGU6ICdQYXRpZW50cyB3aG8gc2hhcmVkIHRoZWlyIGxhYnMgd2l0aCB5b3UnLFxuICAgICAgYWNjZW50OiAnZG9jdG9yJyxcbiAgICB9LFxuICB9LFxuICB7XG4gICAgcGF0aDogJ3BhdGllbnQvOmlkJyxcbiAgICBjb21wb25lbnQ6IERvY3RvclBhdGllbnREZXRhaWxQYWdlQ29tcG9uZW50LFxuICAgIGRhdGE6IHtcbiAgICAgIHRpdGxlOiAnUGF0aWVudCBjYXJkJyxcbiAgICAgIHN1YnRpdGxlOiAnQ2hhcnRzIGFuZCBtZXRyaWNzIGZvciB0aGUgc2VsZWN0ZWQgcGVyaW9kJyxcbiAgICAgIGFjY2VudDogJ2RvY3RvcicsXG4gICAgICBzaG93QmFjazogdHJ1ZSxcbiAgICAgIGJhY2s6ICcvZG9jdG9yJyxcbiAgICB9LFxuICB9LFxuXTtcblxuQE5nTW9kdWxlKHtcbiAgaW1wb3J0czogW1JvdXRlck1vZHVsZS5mb3JDaGlsZChyb3V0ZXMpXSxcbiAgZXhwb3J0czogW1JvdXRlck1vZHVsZV0sXG59KVxuZXhwb3J0IGNsYXNzIERvY3RvclJvdXRpbmdNb2R1bGUge31cbiIsImltcG9ydCB7IENvbXBvbmVudCwgT25Jbml0LCBpbmplY3QgfSBmcm9tICdAYW5ndWxhci9jb3JlJztcbmltcG9ydCB7IFJvdXRlciB9IGZyb20gJ0Bhbmd1bGFyL3JvdXRlcic7XG5cbmltcG9ydCB7IERvY3RvclNlcnZpY2UgfSBmcm9tICcuLi8uLi8uLi8uLi9jb3JlL3NlcnZpY2VzL2RvY3Rvci5zZXJ2aWNlJztcbmltcG9ydCB7IERvY3RvclBhdGllbnRTdW1tYXJ5IH0gZnJvbSAnLi4vLi4vLi4vLi4vY29yZS9tb2RlbHMvZG9jdG9yLm1vZGVsJztcblxuQENvbXBvbmVudCh7XG4gIHNlbGVjdG9yOiAnYXBwLWRvY3Rvci1wYXRpZW50cy1wYWdlJyxcbiAgc3RhbmRhbG9uZTogZmFsc2UsXG4gIHRlbXBsYXRlVXJsOiAnLi9kb2N0b3ItcGF0aWVudHMtcGFnZS5jb21wb25lbnQuaHRtbCcsXG4gIHN0eWxlVXJsczogWycuL2RvY3Rvci1wYXRpZW50cy1wYWdlLmNvbXBvbmVudC5zY3NzJ10sXG59KVxuZXhwb3J0IGNsYXNzIERvY3RvclBhdGllbnRzUGFnZUNvbXBvbmVudCBpbXBsZW1lbnRzIE9uSW5pdCB7XG4gIHByaXZhdGUgcmVhZG9ubHkgZG9jdG9yU2VydmljZSA9IGluamVjdChEb2N0b3JTZXJ2aWNlKTtcbiAgcHJpdmF0ZSByZWFkb25seSByb3V0ZXIgPSBpbmplY3QoUm91dGVyKTtcblxuICBsb2FkaW5nID0gdHJ1ZTtcbiAgcGF0aWVudHM6IERvY3RvclBhdGllbnRTdW1tYXJ5W10gPSBbXTtcbiAgZXJyb3JNZXNzYWdlID0gJyc7XG5cbiAgbmdPbkluaXQoKTogdm9pZCB7XG4gICAgdGhpcy5kb2N0b3JTZXJ2aWNlLmxpc3RQYXRpZW50cygpLnN1YnNjcmliZSh7XG4gICAgICBuZXh0OiAocmVzcG9uc2UpID0+IHtcbiAgICAgICAgdGhpcy5wYXRpZW50cyA9IHJlc3BvbnNlPy5wYXRpZW50cyA/PyBbXTtcbiAgICAgICAgdGhpcy5sb2FkaW5nID0gZmFsc2U7XG4gICAgICB9LFxuICAgICAgZXJyb3I6IChlcnIpID0+IHtcbiAgICAgICAgdGhpcy5lcnJvck1lc3NhZ2UgPSBlcnI/LmVycm9yPy5kZXRhaWwgPz8gJ0ZhaWxlZCB0byBsb2FkIHBhdGllbnRzIGxpc3QuJztcbiAgICAgICAgdGhpcy5sb2FkaW5nID0gZmFsc2U7XG4gICAgICB9LFxuICAgIH0pO1xuICB9XG5cbiAgb3BlblBhdGllbnQocGF0aWVudDogRG9jdG9yUGF0aWVudFN1bW1hcnkpOiB2b2lkIHtcbiAgICB2b2lkIHRoaXMucm91dGVyLm5hdmlnYXRlKFsnL2RvY3Rvci9wYXRpZW50JywgcGF0aWVudC5wYXRpZW50X2lkXSk7XG4gIH1cbn1cbiIsIjxkaXYgY2xhc3M9XCJzcGFjZS15LTZcIj5cbiAgPGFwcC1nbGFzcy1jYXJkIFtleHRyYUNsYXNzXT1cIidnbGFzcy1zdHJvbmcgc3BhY2UteS00J1wiPlxuICAgIDxkaXYgY2xhc3M9XCJmbGV4IGl0ZW1zLWNlbnRlciBqdXN0aWZ5LWJldHdlZW4gZ2FwLTMgZmxleC13cmFwXCI+XG4gICAgICA8ZGl2PlxuICAgICAgICA8aDIgY2xhc3M9XCJ0ZXh0LTJ4bCBmb250LXNlbWlib2xkIHRleHQtW3ZhcigtLXRleHQpXVwiPnt7ICdkb2N0b3IucGF0aWVudHNUaXRsZScgfCB0cmFuc2xhdGUgfX08L2gyPlxuICAgICAgICA8cCBjbGFzcz1cInRleHQtc20gdGV4dC1bdmFyKC0tdGV4dC1kaW0pXVwiPnt7ICdkb2N0b3IucGF0aWVudHNTdWJ0aXRsZScgfCB0cmFuc2xhdGUgfX08L3A+XG4gICAgICA8L2Rpdj5cbiAgICAgIDxzcGFuIGNsYXNzPVwiYmFkZ2UtZ2xhc3NcIj57eyBwYXRpZW50cy5sZW5ndGggfX0ge3sgJ2RvY3Rvci5wYXRpZW50c1RpdGxlJyB8IHRyYW5zbGF0ZSB9fTwvc3Bhbj5cbiAgICA8L2Rpdj5cblxuICAgIDxkaXYgKm5nSWY9XCJsb2FkaW5nXCIgY2xhc3M9XCJmbGV4IGZsZXgtY29sIGl0ZW1zLWNlbnRlciBqdXN0aWZ5LWNlbnRlciBnYXAtMyBweS0xMCB0ZXh0LVt2YXIoLS10ZXh0LWRpbSldXCI+XG4gICAgICA8ZGl2IGNsYXNzPVwiYW5pbWF0ZS1zcGluIGgtMTAgdy0xMCBib3JkZXItMiBib3JkZXItW3ZhcigtLWFjY2VudCldIGJvcmRlci10LXRyYW5zcGFyZW50IHJvdW5kZWQtZnVsbFwiPjwvZGl2PlxuICAgICAge3sgJ2RvY3Rvci5wYXRpZW50c0xvYWRpbmcnIHwgdHJhbnNsYXRlIH19XG4gICAgPC9kaXY+XG5cbiAgICA8ZGl2ICpuZ0lmPVwiIWxvYWRpbmcgJiYgZXJyb3JNZXNzYWdlXCIgY2xhc3M9XCJnbGFzcyBnbGFzcy1zdHJvbmcgdGV4dC1bdmFyKC0tZGFuZ2VyKV0gcC00XCI+XG4gICAgICB7eyBlcnJvck1lc3NhZ2UgfX1cbiAgICA8L2Rpdj5cblxuICAgIDxkaXYgKm5nSWY9XCIhbG9hZGluZyAmJiAhZXJyb3JNZXNzYWdlICYmIHBhdGllbnRzLmxlbmd0aCA9PT0gMFwiIGNsYXNzPVwidGV4dC1zbSB0ZXh0LVt2YXIoLS10ZXh0LWRpbSldXCI+XG4gICAgICB7eyAnZG9jdG9yLnBhdGllbnRzRW1wdHknIHwgdHJhbnNsYXRlIH19XG4gICAgPC9kaXY+XG5cbiAgICA8ZGl2IGNsYXNzPVwiZmxleCBmbGV4LWNvbCBnYXAtM1wiICpuZ0lmPVwiIWxvYWRpbmcgJiYgcGF0aWVudHMubGVuZ3RoXCI+XG4gICAgICA8YnV0dG9uXG4gICAgICAgIHR5cGU9XCJidXR0b25cIlxuICAgICAgICBjbGFzcz1cImdsYXNzIGdsYXNzLXN0cm9uZyBmbGV4IGZsZXgtY29sIHNtOmZsZXgtcm93IHNtOml0ZW1zLWNlbnRlciBzbTpqdXN0aWZ5LWJldHdlZW4gZ2FwLTIgcC00IHRleHQtbGVmdCByb3VuZGVkLVt2YXIoLS1yLWxnKV0gdHJhbnNpdGlvbi10cmFuc2Zvcm1cIlxuICAgICAgICAqbmdGb3I9XCJsZXQgcGF0aWVudCBvZiBwYXRpZW50c1wiXG4gICAgICAgIChjbGljayk9XCJvcGVuUGF0aWVudChwYXRpZW50KVwiXG4gICAgICA+XG4gICAgICAgIDxkaXY+XG4gICAgICAgICAgPHAgY2xhc3M9XCJ0ZXh0LXNtIGZvbnQtc2VtaWJvbGQgdGV4dC1bdmFyKC0tdGV4dCldXCI+e3sgcGF0aWVudC5lbWFpbCB9fTwvcD5cbiAgICAgICAgICA8cCBjbGFzcz1cInRleHQteHMgdGV4dC1bdmFyKC0tdGV4dC1kaW0pXVwiPnt7ICdkb2N0b3IuZ3JhbnRlZEF0JyB8IHRyYW5zbGF0ZSB9fSB7eyBwYXRpZW50LmdyYW50ZWRfYXQgfCBkYXRlOiAnZCBNTU1NIHl5eXksIEhIOm1tJyB9fTwvcD5cbiAgICAgICAgPC9kaXY+XG4gICAgICAgIDxzcGFuIGNsYXNzPVwiYmFkZ2UtZ2xhc3MgYmFkZ2UtYWNjZW50XCI+XG4gICAgICAgICAge3sgJ2RvY3Rvci5sYXRlc3RBbmFseXNpcycgfCB0cmFuc2xhdGUgfX0ge3sgcGF0aWVudC5sYXRlc3RfdGFrZW5fYXQgPyAocGF0aWVudC5sYXRlc3RfdGFrZW5fYXQgfCBkYXRlOiAnZCBNTU0geXl5eScpIDogJy0nIH19XG4gICAgICAgIDwvc3Bhbj5cbiAgICAgIDwvYnV0dG9uPlxuICAgIDwvZGl2PlxuICA8L2FwcC1nbGFzcy1jYXJkPlxuPC9kaXY+XG4iLCJpbXBvcnQgeyBDb21wb25lbnQsIE9uRGVzdHJveSwgT25Jbml0LCBWaWV3Q2hpbGQsIGluamVjdCB9IGZyb20gJ0Bhbmd1bGFyL2NvcmUnO1xuaW1wb3J0IHsgQWN0aXZhdGVkUm91dGUgfSBmcm9tICdAYW5ndWxhci9yb3V0ZXInO1xuaW1wb3J0IHsgQmFzZUNoYXJ0RGlyZWN0aXZlIH0gZnJvbSAnbmcyLWNoYXJ0cyc7XG5pbXBvcnQgeyBTdWJzY3JpcHRpb24gfSBmcm9tICdyeGpzJztcbmltcG9ydCBDaGFydCBmcm9tICdjaGFydC5qcy9hdXRvJztcbmltcG9ydCB6b29tUGx1Z2luIGZyb20gJ2NoYXJ0anMtcGx1Z2luLXpvb20nO1xuaW1wb3J0IHsgQ2hhcnRDb25maWd1cmF0aW9uIH0gZnJvbSAnY2hhcnQuanMnO1xuaW1wb3J0ICdjaGFydGpzLWFkYXB0ZXItZGF0ZS1mbnMnO1xuXG5pbXBvcnQgeyBEb2N0b3JTZXJ2aWNlIH0gZnJvbSAnLi4vLi4vLi4vLi4vY29yZS9zZXJ2aWNlcy9kb2N0b3Iuc2VydmljZSc7XG5pbXBvcnQgeyBNZXRyaWNTZXJpZXNQb2ludCB9IGZyb20gJy4uLy4uLy4uLy4uL2NvcmUvbW9kZWxzL2FuYWx5c2lzLm1vZGVsJztcblxuQ2hhcnQucmVnaXN0ZXIoem9vbVBsdWdpbik7XG5cbmNvbnN0IERFRkFVTFRfTUVUUklDUyA9IFsnR2x1Y29zZScsICdIZW1vZ2xvYmluJywgJ0FMVCcsICdBU1QnLCAnQ3JlYXRpbmluZScsICdUU0gnXTtcblxuLy8gUmVmZXJlbmNlIHJhbmdlIHBsdWdpbiAoc2FtZSBhcyBpbiBwYXRpZW50IGNoYXJ0cylcbmludGVyZmFjZSBOb3JtQmFuZFBsdWdpbk9wdGlvbnMge1xuICByYW5nZXM6IE1ldHJpY1Nlcmllc1BvaW50W107XG4gIGZpbGxTdHlsZTogc3RyaW5nO1xufVxuXG5jb25zdCBub3JtQmFuZFBsdWdpbiA9IHtcbiAgaWQ6ICdub3JtQmFuZCcsXG4gIGJlZm9yZURhdGFzZXRzRHJhdyhjaGFydDogQ2hhcnQsIF9hcmdzOiB1bmtub3duLCBvcHRpb25zPzogTm9ybUJhbmRQbHVnaW5PcHRpb25zKSB7XG4gICAgY29uc3QgcmFuZ2VzID0gb3B0aW9ucz8ucmFuZ2VzID8/IFtdO1xuICAgIGlmICghcmFuZ2VzLmxlbmd0aCkge1xuICAgICAgcmV0dXJuO1xuICAgIH1cblxuICAgIGNvbnN0IG1ldGEgPSBjaGFydC5nZXREYXRhc2V0TWV0YSgwKTtcbiAgICBpZiAoIW1ldGE/LmRhdGE/Lmxlbmd0aCkge1xuICAgICAgcmV0dXJuO1xuICAgIH1cblxuICAgIGNvbnN0IHsgY3R4LCBzY2FsZXMsIGNoYXJ0QXJlYSB9ID0gY2hhcnQ7XG4gICAgY29uc3QgeVNjYWxlID0gc2NhbGVzWyd5J107XG4gICAgY29uc3QgeFNjYWxlID0gc2NhbGVzWyd4J107XG5cbiAgICBpZiAoIXlTY2FsZSB8fCAheFNjYWxlIHx8ICFjaGFydEFyZWEpIHtcbiAgICAgIHJldHVybjtcbiAgICB9XG5cbiAgICAvLyBGaW5kIGdsb2JhbCBtaW4gYW5kIG1heCByZWZlcmVuY2UgdmFsdWVzIGFjcm9zcyBhbGwgcG9pbnRzXG4gICAgY29uc3QgdmFsaWRSZWZzID0gcmFuZ2VzXG4gICAgICAuZmlsdGVyKChwb2ludCkgPT5cbiAgICAgICAgcG9pbnQ/LnJlZk1pbiAhPT0gbnVsbCAmJlxuICAgICAgICBwb2ludD8ucmVmTWluICE9PSB1bmRlZmluZWQgJiZcbiAgICAgICAgcG9pbnQ/LnJlZk1heCAhPT0gbnVsbCAmJlxuICAgICAgICBwb2ludD8ucmVmTWF4ICE9PSB1bmRlZmluZWRcbiAgICAgIClcbiAgICAgIC5tYXAoKHBvaW50KSA9PiAoeyByZWZNaW46IHBvaW50LnJlZk1pbiEsIHJlZk1heDogcG9pbnQucmVmTWF4ISB9KSk7XG5cbiAgICBpZiAoIXZhbGlkUmVmcy5sZW5ndGgpIHtcbiAgICAgIHJldHVybjtcbiAgICB9XG5cbiAgICAvLyBHZXQgZ2xvYmFsIG1pbiBhbmQgbWF4ICh1c2UgZmlyc3QgcG9pbnQncyB2YWx1ZXMgYXMgYmFzZWxpbmUpXG4gICAgY29uc3QgZ2xvYmFsUmVmTWluID0gdmFsaWRSZWZzWzBdLnJlZk1pbjtcbiAgICBjb25zdCBnbG9iYWxSZWZNYXggPSB2YWxpZFJlZnNbMF0ucmVmTWF4O1xuXG4gICAgLy8gRHJhdyBob3Jpem9udGFsIGRhc2hlZCBsaW5lcyBmb3IgbWluIGFuZCBtYXggcmVmZXJlbmNlIHZhbHVlc1xuICAgIGN0eC5zYXZlKCk7XG4gICAgY3R4LnN0cm9rZVN0eWxlID0gJ3JnYmEoMTE4LCAxNjgsIDI1NSwgMC44NSknOyAgLy8gTW9yZSB2aXNpYmxlXG4gICAgY3R4LnNldExpbmVEYXNoKFs4LCA0XSk7XG4gICAgY3R4LmxpbmVXaWR0aCA9IDI7ICAvLyBUaGlja2VyIGxpbmVcblxuICAgIC8vIERyYXcgbWluIHJlZmVyZW5jZSBsaW5lIChob3Jpem9udGFsIGFjcm9zcyBlbnRpcmUgY2hhcnQpXG4gICAgY29uc3QgeU1pbiA9IHlTY2FsZS5nZXRQaXhlbEZvclZhbHVlKGdsb2JhbFJlZk1pbik7XG4gICAgaWYgKE51bWJlci5pc0Zpbml0ZSh5TWluKSkge1xuICAgICAgY3R4LmJlZ2luUGF0aCgpO1xuICAgICAgY3R4Lm1vdmVUbyhjaGFydEFyZWEubGVmdCwgeU1pbik7XG4gICAgICBjdHgubGluZVRvKGNoYXJ0QXJlYS5yaWdodCwgeU1pbik7XG4gICAgICBjdHguc3Ryb2tlKCk7XG4gICAgfVxuXG4gICAgLy8gRHJhdyBtYXggcmVmZXJlbmNlIGxpbmUgKGhvcml6b250YWwgYWNyb3NzIGVudGlyZSBjaGFydClcbiAgICBjb25zdCB5TWF4ID0geVNjYWxlLmdldFBpeGVsRm9yVmFsdWUoZ2xvYmFsUmVmTWF4KTtcbiAgICBpZiAoTnVtYmVyLmlzRmluaXRlKHlNYXgpKSB7XG4gICAgICBjdHguYmVnaW5QYXRoKCk7XG4gICAgICBjdHgubW92ZVRvKGNoYXJ0QXJlYS5sZWZ0LCB5TWF4KTtcbiAgICAgIGN0eC5saW5lVG8oY2hhcnRBcmVhLnJpZ2h0LCB5TWF4KTtcbiAgICAgIGN0eC5zdHJva2UoKTtcbiAgICB9XG5cbiAgICBjdHgucmVzdG9yZSgpO1xuXG4gICAgLy8gT3B0aW9uYWw6IERyYXcgZmlsbGVkIGJhbmQgYmV0d2VlbiBtaW4gYW5kIG1heCAoc3VidGxlIGJhY2tncm91bmQpXG4gICAgY29uc3Qgc2VnbWVudHMgPSBtZXRhLmRhdGFcbiAgICAgIC5tYXAoKGVsZW1lbnQsIGluZGV4KSA9PiB7XG4gICAgICAgIGNvbnN0IHBvaW50ID0gcmFuZ2VzW2luZGV4XTtcbiAgICAgICAgaWYgKCFwb2ludCB8fCBwb2ludC5yZWZNaW4gPT09IG51bGwgfHwgcG9pbnQucmVmTWF4ID09PSBudWxsIHx8IHBvaW50LnJlZk1pbiA9PT0gdW5kZWZpbmVkIHx8IHBvaW50LnJlZk1heCA9PT0gdW5kZWZpbmVkKSB7XG4gICAgICAgICAgcmV0dXJuIG51bGw7XG4gICAgICAgIH1cbiAgICAgICAgY29uc3QgcG9pbnRFbGVtZW50ID0gZWxlbWVudCBhcyB7IHg6IG51bWJlciB9O1xuICAgICAgICBjb25zdCB4ID0gcG9pbnRFbGVtZW50Lng7XG4gICAgICAgIGNvbnN0IHlNaW5QaXggPSB5U2NhbGUuZ2V0UGl4ZWxGb3JWYWx1ZShwb2ludC5yZWZNaW4pO1xuICAgICAgICBjb25zdCB5TWF4UGl4ID0geVNjYWxlLmdldFBpeGVsRm9yVmFsdWUocG9pbnQucmVmTWF4KTtcbiAgICAgICAgaWYgKCFOdW1iZXIuaXNGaW5pdGUoeCkgfHwgIU51bWJlci5pc0Zpbml0ZSh5TWluUGl4KSB8fCAhTnVtYmVyLmlzRmluaXRlKHlNYXhQaXgpKSB7XG4gICAgICAgICAgcmV0dXJuIG51bGw7XG4gICAgICAgIH1cbiAgICAgICAgcmV0dXJuIHsgeCwgeU1pbjogeU1pblBpeCwgeU1heDogeU1heFBpeCB9O1xuICAgICAgfSlcbiAgICAgIC5maWx0ZXIoKHNlZyk6IHNlZyBpcyB7IHg6IG51bWJlcjsgeU1pbjogbnVtYmVyOyB5TWF4OiBudW1iZXIgfSA9PiBzZWcgIT09IG51bGwpO1xuXG4gICAgaWYgKHNlZ21lbnRzLmxlbmd0aCkge1xuICAgICAgY3R4LnNhdmUoKTtcbiAgICAgIGN0eC5iZWdpblBhdGgoKTtcbiAgICAgIGN0eC5maWxsU3R5bGUgPSBvcHRpb25zPy5maWxsU3R5bGUgPz8gJ3JnYmEoMTE4LCAxNjgsIDI1NSwgMC4wOCknO1xuXG4gICAgICBjdHgubW92ZVRvKHNlZ21lbnRzWzBdLngsIHNlZ21lbnRzWzBdLnlNYXgpO1xuICAgICAgc2VnbWVudHMuZm9yRWFjaCgoc2VnKSA9PiBjdHgubGluZVRvKHNlZy54LCBzZWcueU1heCkpO1xuICAgICAgZm9yIChsZXQgaSA9IHNlZ21lbnRzLmxlbmd0aCAtIDE7IGkgPj0gMDsgaS0tKSB7XG4gICAgICAgIGNvbnN0IHNlZyA9IHNlZ21lbnRzW2ldO1xuICAgICAgICBjdHgubGluZVRvKHNlZy54LCBzZWcueU1pbik7XG4gICAgICB9XG4gICAgICBjdHguY2xvc2VQYXRoKCk7XG4gICAgICBjdHguZmlsbCgpO1xuICAgICAgY3R4LnJlc3RvcmUoKTtcbiAgICB9XG4gIH0sXG59O1xuXG4vLyBSZWdpc3RlciBwbHVnaW4gb25seSBpZiBub3QgYWxyZWFkeSByZWdpc3RlcmVkXG5pZiAoIUNoYXJ0LnJlZ2lzdHJ5Py5nZXRQbHVnaW4oJ25vcm1CYW5kJykpIHtcbiAgQ2hhcnQucmVnaXN0ZXIobm9ybUJhbmRQbHVnaW4pO1xufVxuXG5AQ29tcG9uZW50KHtcbiAgc2VsZWN0b3I6ICdhcHAtZG9jdG9yLXBhdGllbnQtZGV0YWlsLXBhZ2UnLFxuICBzdGFuZGFsb25lOiBmYWxzZSxcbiAgdGVtcGxhdGVVcmw6ICcuL2RvY3Rvci1wYXRpZW50LWRldGFpbC1wYWdlLmNvbXBvbmVudC5odG1sJyxcbiAgc3R5bGVVcmxzOiBbJy4vZG9jdG9yLXBhdGllbnQtZGV0YWlsLXBhZ2UuY29tcG9uZW50LnNjc3MnXSxcbn0pXG5leHBvcnQgY2xhc3MgRG9jdG9yUGF0aWVudERldGFpbFBhZ2VDb21wb25lbnQgaW1wbGVtZW50cyBPbkluaXQsIE9uRGVzdHJveSB7XG4gIHByaXZhdGUgcmVhZG9ubHkgZG9jdG9yU2VydmljZSA9IGluamVjdChEb2N0b3JTZXJ2aWNlKTtcbiAgcHJpdmF0ZSByZWFkb25seSByb3V0ZSA9IGluamVjdChBY3RpdmF0ZWRSb3V0ZSk7XG5cbiAgQFZpZXdDaGlsZChCYXNlQ2hhcnREaXJlY3RpdmUpIGNoYXJ0PzogQmFzZUNoYXJ0RGlyZWN0aXZlO1xuXG4gIHBhdGllbnRJZCA9ICcnO1xuICBtZXRyaWNPcHRpb25zID0gREVGQVVMVF9NRVRSSUNTO1xuICBzZWxlY3RlZE1ldHJpYyA9IHRoaXMubWV0cmljT3B0aW9uc1swXTtcbiAgbG9hZGluZyA9IHRydWU7XG4gIHNlcmllczogTWV0cmljU2VyaWVzUG9pbnRbXSA9IFtdO1xuICBlcnJvck1lc3NhZ2UgPSAnJztcbiAgcHJpdmF0ZSBzdWI/OiBTdWJzY3JpcHRpb247XG5cbiAgY2hhcnREYXRhOiBDaGFydENvbmZpZ3VyYXRpb25bJ2RhdGEnXSA9IHsgbGFiZWxzOiBbXSwgZGF0YXNldHM6IFtdIH07XG4gIGNoYXJ0T3B0aW9uczogQ2hhcnRDb25maWd1cmF0aW9uWydvcHRpb25zJ10gPSB7XG4gICAgcmVzcG9uc2l2ZTogdHJ1ZSxcbiAgICBtYWludGFpbkFzcGVjdFJhdGlvOiBmYWxzZSxcbiAgICBzY2FsZXM6IHtcbiAgICAgIHg6IHtcbiAgICAgICAgdHlwZTogJ3RpbWUnLFxuICAgICAgICB0aW1lOiB7IHVuaXQ6ICdkYXknIH0sXG4gICAgICAgIHRpdGxlOiB7IGRpc3BsYXk6IHRydWUsIHRleHQ6ICdEYXRlJyB9LFxuICAgICAgICB0aWNrczogeyBjb2xvcjogJ3JnYmEoMjMyLCAyMzYsIDI0OCwgMC41NSknIH0sXG4gICAgICAgIGdyaWQ6IHsgY29sb3I6ICdyZ2JhKDIzMiwgMjM2LCAyNDgsIDAuMDYpJywgbGluZVdpZHRoOiAwLjUgfSxcbiAgICAgIH0sXG4gICAgICB5OiB7XG4gICAgICAgIHRpdGxlOiB7XG4gICAgICAgICAgZGlzcGxheTogZmFsc2UsICAvLyBXaWxsIGJlIHVwZGF0ZWQgZHluYW1pY2FsbHkgd2l0aCB1bml0IGluIHVwZGF0ZUNoYXJ0KClcbiAgICAgICAgICB0ZXh0OiAnJyxcbiAgICAgICAgfSxcbiAgICAgICAgdGlja3M6IHsgY29sb3I6ICdyZ2JhKDIzMiwgMjM2LCAyNDgsIDAuNTUpJyB9LFxuICAgICAgICBncmlkOiB7IGNvbG9yOiAncmdiYSgyMzIsIDIzNiwgMjQ4LCAwLjA1KScsIGxpbmVXaWR0aDogMC41IH0sXG4gICAgICB9LFxuICAgIH0sXG4gICAgcGx1Z2luczoge1xuICAgICAgem9vbToge1xuICAgICAgICBwYW46IHtcbiAgICAgICAgICBlbmFibGVkOiB0cnVlLFxuICAgICAgICAgIG1vZGU6ICd4eScsICAvLyBBbGxvdyBwYW5uaW5nIG9uIGJvdGggWCBhbmQgWSBheGVzXG4gICAgICAgIH0sXG4gICAgICAgIHpvb206IHtcbiAgICAgICAgICB3aGVlbDogeyBlbmFibGVkOiB0cnVlIH0sXG4gICAgICAgICAgcGluY2g6IHsgZW5hYmxlZDogdHJ1ZSB9LFxuICAgICAgICAgIG1vZGU6ICd4eScsICAvLyBBbGxvdyB6b29taW5nIG9uIGJvdGggWCBhbmQgWSBheGVzXG4gICAgICAgIH0sXG4gICAgICB9LFxuICAgICAgbm9ybUJhbmQ6IHtcbiAgICAgICAgcmFuZ2VzOiBbXSxcbiAgICAgICAgZmlsbFN0eWxlOiAncmdiYSgxMTgsIDE2OCwgMjU1LCAwLjA4KScsXG4gICAgICB9IGFzIGFueSwgIC8vIEN1c3RvbSBwbHVnaW4gdHlwZVxuICAgIH0gYXMgYW55LFxuICB9O1xuXG4gIG5nT25Jbml0KCk6IHZvaWQge1xuICAgIHRoaXMuc3ViID0gdGhpcy5yb3V0ZS5wYXJhbU1hcC5zdWJzY3JpYmUoKHBhcmFtcykgPT4ge1xuICAgICAgdGhpcy5wYXRpZW50SWQgPSBwYXJhbXMuZ2V0KCdpZCcpID8/ICcnO1xuICAgICAgaWYgKHRoaXMucGF0aWVudElkKSB7XG4gICAgICAgIHRoaXMubG9hZFNlcmllcygpO1xuICAgICAgfVxuICAgIH0pO1xuICB9XG5cbiAgbmdPbkRlc3Ryb3koKTogdm9pZCB7XG4gICAgdGhpcy5zdWI/LnVuc3Vic2NyaWJlKCk7XG4gIH1cblxuICBvbk1ldHJpY0NoYW5nZShtZXRyaWM6IHN0cmluZyk6IHZvaWQge1xuICAgIGlmICh0aGlzLnNlbGVjdGVkTWV0cmljID09PSBtZXRyaWMpIHtcbiAgICAgIHJldHVybjtcbiAgICB9XG4gICAgdGhpcy5zZWxlY3RlZE1ldHJpYyA9IG1ldHJpYztcbiAgICB0aGlzLmxvYWRTZXJpZXMoKTtcbiAgfVxuXG4gIHByaXZhdGUgbG9hZFNlcmllcygpOiB2b2lkIHtcbiAgICBpZiAoIXRoaXMucGF0aWVudElkIHx8ICF0aGlzLnNlbGVjdGVkTWV0cmljKSB7XG4gICAgICByZXR1cm47XG4gICAgfVxuICAgIHRoaXMubG9hZGluZyA9IHRydWU7XG4gICAgdGhpcy5lcnJvck1lc3NhZ2UgPSAnJztcbiAgICB0aGlzLmRvY3RvclNlcnZpY2UuZ2V0U2VyaWVzKHRoaXMucGF0aWVudElkLCB0aGlzLnNlbGVjdGVkTWV0cmljKS5zdWJzY3JpYmUoe1xuICAgICAgbmV4dDogKHNlcmllcykgPT4ge1xuICAgICAgICB0aGlzLnNlcmllcyA9IHNlcmllcztcbiAgICAgICAgdGhpcy51cGRhdGVDaGFydCgpO1xuICAgICAgICB0aGlzLmxvYWRpbmcgPSBmYWxzZTtcbiAgICAgIH0sXG4gICAgICBlcnJvcjogKGVycikgPT4ge1xuICAgICAgICB0aGlzLmVycm9yTWVzc2FnZSA9IGVycj8uZXJyb3I/LmRldGFpbCA/PyAnRmFpbGVkIHRvIGxvYWQgdGltZSBzZXJpZXMuJztcbiAgICAgICAgdGhpcy5sb2FkaW5nID0gZmFsc2U7XG4gICAgICB9LFxuICAgIH0pO1xuICB9XG5cbiAgcHJpdmF0ZSBjYWxjdWxhdGVZQXhpc01pbihyYW5nZXM6IE1ldHJpY1Nlcmllc1BvaW50W10pOiBudW1iZXIgfCB1bmRlZmluZWQge1xuICAgIGlmICghcmFuZ2VzLmxlbmd0aCkgcmV0dXJuIHVuZGVmaW5lZDtcblxuICAgIGNvbnN0IHZhbHVlcyA9IHJhbmdlcy5tYXAocCA9PiBwLnkpLmZpbHRlcih2ID0+IHYgIT0gbnVsbCk7XG4gICAgY29uc3QgcmVmTWlucyA9IHJhbmdlcy5tYXAocCA9PiBwLnJlZk1pbikuZmlsdGVyKHYgPT4gdiAhPSBudWxsKSBhcyBudW1iZXJbXTtcblxuICAgIGlmICghdmFsdWVzLmxlbmd0aCkgcmV0dXJuIHVuZGVmaW5lZDtcblxuICAgIGNvbnN0IGRhdGFNaW4gPSBNYXRoLm1pbiguLi52YWx1ZXMpO1xuICAgIGNvbnN0IHJlZk1pbiA9IHJlZk1pbnMubGVuZ3RoID8gTWF0aC5taW4oLi4ucmVmTWlucykgOiBudWxsO1xuXG4gICAgY29uc3QgbWluVmFsdWUgPSByZWZNaW4gIT0gbnVsbCA/IE1hdGgubWluKGRhdGFNaW4sIHJlZk1pbikgOiBkYXRhTWluO1xuICAgIHJldHVybiBtaW5WYWx1ZSAqIDAuOTsgIC8vIDEwJSBwYWRkaW5nXG4gIH1cblxuICBwcml2YXRlIGNhbGN1bGF0ZVlBeGlzTWF4KHJhbmdlczogTWV0cmljU2VyaWVzUG9pbnRbXSk6IG51bWJlciB8IHVuZGVmaW5lZCB7XG4gICAgaWYgKCFyYW5nZXMubGVuZ3RoKSByZXR1cm4gdW5kZWZpbmVkO1xuXG4gICAgY29uc3QgdmFsdWVzID0gcmFuZ2VzLm1hcChwID0+IHAueSkuZmlsdGVyKHYgPT4gdiAhPSBudWxsKTtcbiAgICBjb25zdCByZWZNYXhzID0gcmFuZ2VzLm1hcChwID0+IHAucmVmTWF4KS5maWx0ZXIodiA9PiB2ICE9IG51bGwpIGFzIG51bWJlcltdO1xuXG4gICAgaWYgKCF2YWx1ZXMubGVuZ3RoKSByZXR1cm4gdW5kZWZpbmVkO1xuXG4gICAgY29uc3QgZGF0YU1heCA9IE1hdGgubWF4KC4uLnZhbHVlcyk7XG4gICAgY29uc3QgcmVmTWF4ID0gcmVmTWF4cy5sZW5ndGggPyBNYXRoLm1heCguLi5yZWZNYXhzKSA6IG51bGw7XG5cbiAgICBjb25zdCBtYXhWYWx1ZSA9IHJlZk1heCAhPSBudWxsID8gTWF0aC5tYXgoZGF0YU1heCwgcmVmTWF4KSA6IGRhdGFNYXg7XG4gICAgcmV0dXJuIG1heFZhbHVlICogMS4xOyAgLy8gMTAlIHBhZGRpbmdcbiAgfVxuXG4gIHByaXZhdGUgdXBkYXRlQ2hhcnQoKTogdm9pZCB7XG4gICAgY29uc3QgbGFiZWxzID0gdGhpcy5zZXJpZXMubWFwKChwb2ludCkgPT4gcG9pbnQudCk7XG4gICAgY29uc3QgZGF0YSA9IHRoaXMuc2VyaWVzLm1hcCgocG9pbnQpID0+IHBvaW50LnkpO1xuXG4gICAgLy8gRXh0cmFjdCB1bml0IGZyb20gZmlyc3QgcG9pbnQgKGFsbCBwb2ludHMgc2hvdWxkIGhhdmUgdGhlIHNhbWUgdW5pdClcbiAgICBjb25zdCB1bml0ID0gdGhpcy5zZXJpZXMubGVuZ3RoID4gMCAmJiB0aGlzLnNlcmllc1swXT8udW5pdCA/IHRoaXMuc2VyaWVzWzBdLnVuaXQgOiBudWxsO1xuICAgIGNvbnN0IHlBeGlzVGl0bGUgPSB1bml0IHx8ICcnO1xuXG4gICAgdGhpcy5jaGFydERhdGEgPSB7XG4gICAgICBsYWJlbHMsXG4gICAgICBkYXRhc2V0czogW1xuICAgICAgICB7XG4gICAgICAgICAgbGFiZWw6IHRoaXMuc2VsZWN0ZWRNZXRyaWMsXG4gICAgICAgICAgZGF0YSxcbiAgICAgICAgICBib3JkZXJDb2xvcjogJyM3NmE4ZmYnLFxuICAgICAgICAgIGJhY2tncm91bmRDb2xvcjogJ3JnYmEoMTE4LCAxNjgsIDI1NSwgMC4yNSknLFxuICAgICAgICAgIHRlbnNpb246IDAuMjUsXG4gICAgICAgICAgZmlsbDogZmFsc2UsXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgIH07XG5cbiAgICAvLyBVcGRhdGUgWS1heGlzIHRpdGxlIGFuZCByYW5nZSB3aXRoIHVuaXRcbiAgICBpZiAodGhpcy5jaGFydE9wdGlvbnM/LnNjYWxlcz8uWyd5J10pIHtcbiAgICAgIGNvbnN0IHlTY2FsZSA9IHRoaXMuY2hhcnRPcHRpb25zLnNjYWxlc1sneSddIGFzIGFueTtcbiAgICAgIGlmICh5U2NhbGUpIHtcbiAgICAgICAgeVNjYWxlLnRpdGxlID0ge1xuICAgICAgICAgIGRpc3BsYXk6ICEheUF4aXNUaXRsZSxcbiAgICAgICAgICB0ZXh0OiB5QXhpc1RpdGxlLFxuICAgICAgICAgIGNvbG9yOiAncmdiYSgyMzIsIDIzNiwgMjQ4LCAwLjc1KScsXG4gICAgICAgICAgZm9udDoge1xuICAgICAgICAgICAgc2l6ZTogMTIsXG4gICAgICAgICAgICBmYW1pbHk6ICdJbnRlciwgc3lzdGVtLXVpLCBzYW5zLXNlcmlmJyxcbiAgICAgICAgICAgIHdlaWdodDogNTAwLFxuICAgICAgICAgIH0sXG4gICAgICAgICAgcGFkZGluZzogeyB0b3A6IDAsIGJvdHRvbTogOCB9LFxuICAgICAgICB9O1xuICAgICAgICAvLyBBdXRvLWFkanVzdCBZLWF4aXMgcmFuZ2UgdG8gaW5jbHVkZSByZWZlcmVuY2UgdmFsdWVzXG4gICAgICAgIHlTY2FsZS5taW4gPSB0aGlzLmNhbGN1bGF0ZVlBeGlzTWluKHRoaXMuc2VyaWVzKTtcbiAgICAgICAgeVNjYWxlLm1heCA9IHRoaXMuY2FsY3VsYXRlWUF4aXNNYXgodGhpcy5zZXJpZXMpO1xuICAgICAgfVxuICAgIH1cblxuICAgIC8vIFVwZGF0ZSByZWZlcmVuY2UgcmFuZ2UgcGx1Z2luIHdpdGggc2VyaWVzIGRhdGFcbiAgICBjb25zdCBwbHVnaW5zID0gdGhpcy5jaGFydE9wdGlvbnM/LnBsdWdpbnMgYXMgYW55O1xuICAgIGlmIChwbHVnaW5zPy5ub3JtQmFuZCkge1xuICAgICAgcGx1Z2lucy5ub3JtQmFuZC5yYW5nZXMgPSB0aGlzLnNlcmllcztcbiAgICB9XG5cbiAgICAvLyBEZWJ1ZzogbG9nIHJlZmVyZW5jZSB2YWx1ZXNcbiAgICBjb25zdCB2YWxpZFJlZnMgPSB0aGlzLnNlcmllcy5maWx0ZXIocCA9PiBwLnJlZk1pbiAhPSBudWxsICYmIHAucmVmTWF4ICE9IG51bGwpO1xuICAgIGlmICh2YWxpZFJlZnMubGVuZ3RoID4gMCkge1xuICAgICAgY29uc29sZS5sb2coJ1tDaGFydF0gUmVmZXJlbmNlIHZhbHVlcyBmb3VuZDonLCB7XG4gICAgICAgIGNvdW50OiB2YWxpZFJlZnMubGVuZ3RoLFxuICAgICAgICByZWZNaW46IHZhbGlkUmVmc1swXS5yZWZNaW4sXG4gICAgICAgIHJlZk1heDogdmFsaWRSZWZzWzBdLnJlZk1heCxcbiAgICAgICAgeUF4aXNNaW46IHRoaXMuY2FsY3VsYXRlWUF4aXNNaW4odGhpcy5zZXJpZXMpLFxuICAgICAgICB5QXhpc01heDogdGhpcy5jYWxjdWxhdGVZQXhpc01heCh0aGlzLnNlcmllcyksXG4gICAgICB9KTtcbiAgICB9IGVsc2Uge1xuICAgICAgY29uc29sZS5sb2coJ1tDaGFydF0gTm8gcmVmZXJlbmNlIHZhbHVlcyBmb3VuZCBpbiBzZXJpZXM6JywgdGhpcy5zZXJpZXMpO1xuICAgIH1cblxuICAgIHRoaXMuY2hhcnQ/LnVwZGF0ZSgpO1xuICB9XG59XG4iLCI8ZGl2IGNsYXNzPVwic3BhY2UteS02XCI+XG4gIDxhcHAtZ2xhc3MtY2FyZCBbZXh0cmFDbGFzc109XCInZ2xhc3Mtc3Ryb25nIHNwYWNlLXktNSdcIj5cbiAgICA8ZGl2IGNsYXNzPVwiZmxleCBmbGV4LWNvbCBsZzpmbGV4LXJvdyBsZzppdGVtcy1lbmQgbGc6anVzdGlmeS1iZXR3ZWVuIGdhcC00XCI+XG4gICAgICA8ZGl2PlxuICAgICAgICA8aDIgY2xhc3M9XCJ0ZXh0LTJ4bCBmb250LXNlbWlib2xkIHRleHQtW3ZhcigtLXRleHQpXVwiPnt7ICdkb2N0b3IuZGV0YWlsVGl0bGUnIHwgdHJhbnNsYXRlIH19IHt7IHBhdGllbnRJZCB9fTwvaDI+XG4gICAgICAgIDxwIGNsYXNzPVwidGV4dC1zbSB0ZXh0LVt2YXIoLS10ZXh0LWRpbSldXCI+e3sgJ2RvY3Rvci5kZXRhaWxTdWJ0aXRsZScgfCB0cmFuc2xhdGUgfX08L3A+XG4gICAgICA8L2Rpdj5cbiAgICAgIDxkaXYgY2xhc3M9XCJmbGV4IGZsZXgtd3JhcCBpdGVtcy1jZW50ZXIgZ2FwLTJcIj5cbiAgICAgICAgPHNwYW4gY2xhc3M9XCJ0ZXh0LXhzIHVwcGVyY2FzZSB0cmFja2luZy1bMC4yZW1dIHRleHQtW3ZhcigtLXRleHQtZGltKV1cIj57eyAnZG9jdG9yLm1ldHJpYycgfCB0cmFuc2xhdGUgfX08L3NwYW4+XG4gICAgICAgIDxzZWxlY3QgY2xhc3M9XCJpbnB1dC1nbGFzcyBtaW4tdy1bMjAwcHhdXCIgW25nTW9kZWxdPVwic2VsZWN0ZWRNZXRyaWNcIiAobmdNb2RlbENoYW5nZSk9XCJvbk1ldHJpY0NoYW5nZSgkZXZlbnQpXCI+XG4gICAgICAgICAgPG9wdGlvbiAqbmdGb3I9XCJsZXQgb3B0aW9uIG9mIG1ldHJpY09wdGlvbnNcIiBbbmdWYWx1ZV09XCJvcHRpb25cIj57eyBvcHRpb24gfX08L29wdGlvbj5cbiAgICAgICAgPC9zZWxlY3Q+XG4gICAgICA8L2Rpdj5cbiAgICA8L2Rpdj5cblxuICAgIDxkaXYgKm5nSWY9XCJsb2FkaW5nXCIgY2xhc3M9XCJmbGV4IGZsZXgtY29sIGl0ZW1zLWNlbnRlciBqdXN0aWZ5LWNlbnRlciBnYXAtMyBweS0xMCB0ZXh0LVt2YXIoLS10ZXh0LWRpbSldXCI+XG4gICAgICA8ZGl2IGNsYXNzPVwiYW5pbWF0ZS1zcGluIGgtMTAgdy0xMCBib3JkZXItMiBib3JkZXItW3ZhcigtLWFjY2VudCldIGJvcmRlci10LXRyYW5zcGFyZW50IHJvdW5kZWQtZnVsbFwiPjwvZGl2PlxuICAgICAge3sgJ2RvY3Rvci5sb2FkaW5nJyB8IHRyYW5zbGF0ZSB9fVxuICAgIDwvZGl2PlxuXG4gICAgPGRpdiAqbmdJZj1cIiFsb2FkaW5nICYmIGVycm9yTWVzc2FnZVwiIGNsYXNzPVwiZ2xhc3MgZ2xhc3Mtc3Ryb25nIHRleHQtW3ZhcigtLWRhbmdlcildIHAtNFwiPlxuICAgICAge3sgZXJyb3JNZXNzYWdlIH19XG4gICAgPC9kaXY+XG5cbiAgICA8ZGl2IGNsYXNzPVwiaC1bMjYwcHhdIHNtOmgtWzM0MHB4XVwiICpuZ0lmPVwiIWxvYWRpbmcgJiYgIWVycm9yTWVzc2FnZVwiPlxuICAgICAgPGNhbnZhcyBiYXNlQ2hhcnQgW2RhdGFdPVwiY2hhcnREYXRhXCIgW29wdGlvbnNdPVwiY2hhcnRPcHRpb25zXCIgW3R5cGVdPVwiJ3NjYXR0ZXInXCI+PC9jYW52YXM+XG4gICAgPC9kaXY+XG4gIDwvYXBwLWdsYXNzLWNhcmQ+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LHFCQUFBLG1CQUFBLG1CQUFBLGtCQUFBLGdCQUFBLHNCQUFBLGdDQUFBLHdCQUFBLDJCQUFBLHNCQUFBLHdCQUFBLHdCQUFBLHNCQUFBLDBCQUFBLGNBQUEsaUJBQUEsY0FBQSxpQkFBQSxtQkFBQSwwQkFBQSx3QkFBQSx3QkFBQSxpQkFBQSx1QkFBQSx1QkFBQSxxQkFBQSxxQkFBQSwyQkFBQSxtQkFBQSxZQUFBLGdCQUFBLG9CQUFBLGdCQUFBLHNCQUFBLG9CQUFBLGtCQUFBLGdCQUFBLG1CQUFBLDJCQUFBLHdCQUFBLHVCQUFBLHVCQUFBLHlCQUFBLDJCQUFBLHdCQUFBLGdCQUFBLG9CQUFBLDJCQUFBLGVBQUEsa0JBQUEsc0JBQUEsMEJBQUEsc0JBQUEsbUJBQUEsY0FBQSxvQkFBQSxnQkFBQSxrQkFBQSxrQkFBQSx3QkFBQSx3QkFBQSx3QkFBQSxvQkFBQSxzQkFBQSxxQkFBQSx1QkFBQSxzQkFBN0QsMkJBQTJCLEdBQUEsQ0FBQSxlQUFBLG1CQUFBLG1CQUFBLGNBQUEsZUFBQSxpQkFBQSxpQkFBQSxtQkFBQSxrQkFBQSxjQUFBLG9CQUFBLG9CQUFBLGtCQUFBLGlCQUFBLENBQUE7IiwibmFtZXMiOlsiTmdNb2R1bGUiLCJDb21wb25lbnQiLCJpbmplY3QiLCJpbmplY3QiLCJDb21wb25lbnQiLCJpMCIsIk5nTW9kdWxlIl19