import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { format } from 'date-fns';
import { Subscription } from 'rxjs';

import { V2AnalyteItemResponse, V2DoctorNoteResponse, V2SeriesPointResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../../v2/i18n/analyte-display';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-doctor-patient-detail-page',
  standalone: false,
  templateUrl: './doctor-patient-detail-page.component.html',
  styleUrls: ['./doctor-patient-detail-page.component.scss'],
})
export class DoctorPatientDetailPageComponent implements OnInit, OnDestroy {
  private readonly v2Service = inject(V2Service);
  private readonly route = inject(ActivatedRoute);

  patientId = '';
  patientName = '';
  analytes: V2AnalyteItemResponse[] = [];
  selectedMetric = '';
  loading = true;
  errorMessage = '';
  private sub?: Subscription;

  selectedSeriesPoint: V2SeriesPointResponse | null = null;
  pointNoteText = '';
  noteSaving = false;
  notesLoading = false;
  noteError = '';
  noteSaved = '';
  private pointNotesMap = new Map<string, V2DoctorNoteResponse>();
  private debugNoteLogDone = false;
  readonly language: V2DashboardLang = this.loadLanguage();

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe((params) => {
      this.patientId = params.get('id') ?? '';
      if (this.patientId) {
        this.loadPatientIdentity();
        this.loadAnalytes();
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  get selectedPointDateLabel(): string {
    if (!this.selectedSeriesPoint?.t) {
      return '-';
    }
    const ts = Date.parse(this.selectedSeriesPoint.t);
    if (!Number.isFinite(ts)) {
      return this.selectedSeriesPoint.t;
    }
    return format(new Date(ts), 'dd.MM.yyyy HH:mm');
  }

  onMetricSelect(metric: string): void {
    if (this.selectedMetric === metric) {
      return;
    }
    this.selectedMetric = metric;
    this.selectedSeriesPoint = null;
    this.pointNoteText = '';
    this.noteSaved = '';
    this.noteError = '';
    this.loadDoctorNotesForMetric();
  }

  onSeriesPointSelected(point: V2SeriesPointResponse): void {
    this.selectedSeriesPoint = point;
    this.noteSaved = '';
    this.noteError = '';
    this.pointNoteText = this.pointNotesMap.get(this.toPointKey(point.t))?.note ?? '';
  }

  savePointNote(): void {
    const selectedPoint = this.selectedSeriesPoint;
    if (!this.canSaveContext) {
      this.noteError = this.language === 'es' ? 'Seleccione un punto y paciente valido.' : 'Select a valid patient point first.';
      return;
    }
    const note = this.pointNoteText.trim();
    if (!note) {
      this.noteError = this.language === 'es' ? 'La nota no puede estar vacia.' : 'Note must not be empty.';
      return;
    }
    this.noteSaving = true;
    this.noteSaved = '';
    this.noteError = '';
    if (!environment.production && !this.debugNoteLogDone) {
      const debugUrl = this.v2Service.getDoctorNotesUpsertUrl(this.patientId);
      console.debug('[V2 note save]', {
        patientId: this.patientId,
        analyteKey: this.selectedMetric,
        t: this.selectedSeriesPoint?.t ?? null,
        url: debugUrl,
      });
      this.debugNoteLogDone = true;
    }
    this.v2Service
      .upsertDoctorNote(this.patientId, {
        analyte_key: this.selectedMetric,
        t: selectedPoint?.t ?? '',
        note,
      })
      .subscribe({
        next: (saved) => {
          const key = this.toPointKey(saved.t);
          this.pointNotesMap.set(key, saved);
          this.pointNoteText = saved.note;
          this.noteSaving = false;
          this.noteSaved = this.language === 'es' ? 'Nota guardada.' : 'Note saved.';
        },
        error: (err) => {
          this.noteSaving = false;
          const status = err?.status;
          if (status === 403) {
            this.noteError = this.language === 'es' ? 'Sin acceso para guardar nota (403).' : 'Forbidden: no access to save note (403).';
            return;
          }
          if (status === 404) {
            this.noteError = this.language === 'es' ? 'Ruta no encontrada al guardar nota (404).' : 'Not Found while saving note (404).';
            return;
          }
          this.noteError = err?.error?.detail ?? (this.language === 'es' ? 'No se pudo guardar la nota.' : 'Failed to save note.');
        },
      });
  }

  get canSaveContext(): boolean {
    return Boolean(this.patientId && this.selectedMetric && this.selectedSeriesPoint?.t);
  }

  getAnalyteLabel(analyteKey: string): string {
    return getAnalyteDisplayName(analyteKey, this.language, this.getRawName(analyteKey) || undefined);
  }

  private loadAnalytes(): void {
    this.loading = true;
    this.errorMessage = '';
    this.v2Service.listPatientAnalytes(this.patientId).subscribe({
      next: (analytes) => {
        this.analytes = analytes ?? [];
        const availableKeys = new Set(this.analytes.map((item) => item.analyte_key));
        if (!availableKeys.size) {
          this.selectedMetric = '';
          this.errorMessage = 'No metrics available for this patient yet.';
          this.loading = false;
          return;
        }

        if (!this.selectedMetric || !availableKeys.has(this.selectedMetric)) {
          this.selectedMetric = this.sortAnalytesByDisplay(this.analytes)[0]?.analyte_key ?? '';
        }
        this.loading = false;
        this.loadDoctorNotesForMetric();
      },
      error: (err) => {
        this.analytes = [];
        this.errorMessage = err?.error?.detail ?? 'Failed to load metrics list.';
        this.loading = false;
      },
    });
  }

  private loadDoctorNotesForMetric(): void {
    if (!this.patientId || !this.selectedMetric) {
      this.pointNotesMap = new Map<string, V2DoctorNoteResponse>();
      return;
    }
    this.notesLoading = true;
    this.v2Service.listDoctorNotes(this.patientId, this.selectedMetric).subscribe({
      next: (notes) => {
        const map = new Map<string, V2DoctorNoteResponse>();
        (notes ?? []).forEach((item) => {
          const key = this.toPointKey(item.t);
          if (key) {
            map.set(key, item);
          }
        });
        this.pointNotesMap = map;
        if (this.selectedSeriesPoint) {
          this.pointNoteText = map.get(this.toPointKey(this.selectedSeriesPoint.t))?.note ?? '';
        }
        this.notesLoading = false;
      },
      error: () => {
        this.pointNotesMap = new Map<string, V2DoctorNoteResponse>();
        this.notesLoading = false;
      },
    });
  }

  private loadPatientIdentity(): void {
    this.v2Service.listDoctorPatients().subscribe({
      next: (patients) => {
        const match = (patients ?? []).find((patient) => `${patient.patient_id}` === `${this.patientId}`);
        if (match) {
          this.patientName = match.display_name || match.email || '';
        }
      },
    });
  }

  private getRawName(analyteKey: string): string {
    const match = this.analytes.find((item) => item.analyte_key === analyteKey);
    return match?.raw_name?.trim() ?? '';
  }

  private sortAnalytesByDisplay(items: V2AnalyteItemResponse[]): V2AnalyteItemResponse[] {
    return [...items].sort((a, b) => {
      const labelA = getAnalyteDisplayName(a.analyte_key, this.language, a.raw_name);
      const labelB = getAnalyteDisplayName(b.analyte_key, this.language, b.raw_name);
      return labelA.localeCompare(labelB, this.language);
    });
  }

  private toPointKey(value: string | null): string {
    if (!value) {
      return '';
    }
    const ts = Date.parse(value);
    if (!Number.isFinite(ts)) {
      return value;
    }
    return new Date(ts).toISOString();
  }

  private loadLanguage(): V2DashboardLang {
    const stored = localStorage.getItem('v2_lang');
    return stored === 'es' || stored === 'en' ? stored : 'es';
  }
}
