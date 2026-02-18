import { Component, OnInit, inject } from '@angular/core';
import { format } from 'date-fns';

import { V2AnalyteItemResponse, V2UploadResponse } from '../../../../core/models/v2.model';
import { V2Service } from '../../../../core/services/v2.service';
import { getAnalyteDisplayName, V2DashboardLang } from '../../i18n/analyte-display';

type SortMode = 'recent' | 'az' | 'za';

interface DashboardLabels {
  title: string;
  subtitle: string;
  chooseFile: string;
  uploadAction: string;
  uploading: string;
  listTitle: string;
  loadingAnalytes: string;
  emptyAnalytes: string;
  searchPlaceholder: string;
  sortRecent: string;
  sortAz: string;
  sortZa: string;
  numericOnly: string;
  textOnly: string;
  unknownDate: string;
  unknownValue: string;
  duplicatePrefix: string;
  processedPrefix: string;
  uploadPdfError: string;
  selectPdfError: string;
  uploadFailed: string;
  loadAnalytesFailed: string;
}

const V2_DASHBOARD_COPY: Record<V2DashboardLang, DashboardLabels> = {
  en: {
    title: 'Upload V2 Lab PDF',
    subtitle: 'Only PDF files are accepted.',
    chooseFile: 'Choose PDF',
    uploadAction: 'Upload to V2',
    uploading: 'Uploading...',
    listTitle: 'Analytes',
    loadingAnalytes: 'Loading analytes...',
    emptyAnalytes: 'No analytes found yet. Upload a PDF to create your first V2 document.',
    searchPlaceholder: 'Search by display name, analyte key, raw name...',
    sortRecent: 'Most recent',
    sortAz: 'A -> Z',
    sortZa: 'Z -> A',
    numericOnly: 'Numeric only',
    textOnly: 'Text only',
    unknownDate: '-',
    unknownValue: '-',
    duplicatePrefix: 'Duplicate document. Reused existing id',
    processedPrefix: 'Document processed. Saved',
    uploadPdfError: 'Please upload a PDF file.',
    selectPdfError: 'Please select a PDF file.',
    uploadFailed: 'Upload failed.',
    loadAnalytesFailed: 'Failed to load analytes.',
  },
  es: {
    title: 'Subir PDF de laboratorio V2',
    subtitle: 'Solo se permiten archivos PDF.',
    chooseFile: 'Elegir PDF',
    uploadAction: 'Subir a V2',
    uploading: 'Subiendo...',
    listTitle: 'Analitos',
    loadingAnalytes: 'Cargando analitos...',
    emptyAnalytes: 'Aun no hay analitos. Sube un PDF para crear tu primer documento V2.',
    searchPlaceholder: 'Buscar por nombre, clave o nombre crudo...',
    sortRecent: 'Mas reciente',
    sortAz: 'A -> Z',
    sortZa: 'Z -> A',
    numericOnly: 'Solo numericos',
    textOnly: 'Solo texto',
    unknownDate: '-',
    unknownValue: '-',
    duplicatePrefix: 'Documento duplicado. Se reutilizo el id',
    processedPrefix: 'Documento procesado. Metricas guardadas:',
    uploadPdfError: 'Por favor sube un archivo PDF.',
    selectPdfError: 'Por favor selecciona un archivo PDF.',
    uploadFailed: 'Fallo al subir el archivo.',
    loadAnalytesFailed: 'No se pudieron cargar los analitos.',
  },
};

@Component({
  selector: 'app-v2-dashboard-page',
  standalone: false,
  templateUrl: './v2-dashboard-page.component.html',
  styleUrls: ['./v2-dashboard-page.component.scss'],
})
export class V2DashboardPageComponent implements OnInit {
  private readonly v2Service = inject(V2Service);

  readonly langStorageKey = 'v2_lang';
  readonly sortModes: SortMode[] = ['recent', 'az', 'za'];

  selectedFile: File | null = null;
  isUploading = false;
  isLoadingAnalytes = true;
  analytes: V2AnalyteItemResponse[] = [];
  visibleAnalytes: V2AnalyteItemResponse[] = [];
  uploadMessage = '';
  errorMessage = '';
  isDragging = false;
  language: V2DashboardLang = 'es';
  searchTerm = '';
  sortMode: SortMode = 'recent';
  numericOnly = false;
  textOnly = false;

  ngOnInit(): void {
    this.language = this.loadLanguage();
    this.loadAnalytes();
  }

  get copy(): DashboardLabels {
    return V2_DASHBOARD_COPY[this.language];
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.setFile(input.files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
    const dropped = Array.from(event.dataTransfer?.files ?? []);
    const file = dropped.find((f) => f.type === 'application/pdf');
    if (!file) {
      this.errorMessage = this.copy.uploadPdfError;
      return;
    }
    this.setFile(file);
  }

  upload(): void {
    if (!this.selectedFile) {
      this.errorMessage = this.copy.selectPdfError;
      return;
    }
    this.errorMessage = '';
    this.uploadMessage = '';
    this.isUploading = true;

    this.v2Service.uploadDocument(this.selectedFile).subscribe({
      next: (res) => {
        this.isUploading = false;
        this.uploadMessage = this.formatUploadMessage(res);
        this.loadAnalytes();
      },
      error: (err) => {
        this.isUploading = false;
        this.errorMessage = err?.error?.detail ?? this.copy.uploadFailed;
      },
    });
  }

  clearFile(): void {
    this.selectedFile = null;
    this.uploadMessage = '';
    this.errorMessage = '';
  }

  setLanguage(lang: V2DashboardLang): void {
    if (this.language === lang) {
      return;
    }
    this.language = lang;
    localStorage.setItem(this.langStorageKey, lang);
    this.refreshVisibleAnalytes();
  }

  onSearchTermChange(term: string): void {
    this.searchTerm = term;
    this.refreshVisibleAnalytes();
  }

  setSortMode(mode: SortMode): void {
    this.sortMode = mode;
    this.refreshVisibleAnalytes();
  }

  toggleNumericOnly(next: boolean): void {
    this.numericOnly = next;
    if (next) {
      this.textOnly = false;
    }
    this.refreshVisibleAnalytes();
  }

  toggleTextOnly(next: boolean): void {
    this.textOnly = next;
    if (next) {
      this.numericOnly = false;
    }
    this.refreshVisibleAnalytes();
  }

  getPrimaryLabel(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.language, item.raw_name);
  }

  getSecondaryLabel(item: V2AnalyteItemResponse): string {
    const raw = item.raw_name?.trim();
    if (raw && raw.toUpperCase() !== item.analyte_key.toUpperCase()) {
      return `${item.analyte_key} | ${raw}`;
    }
    return item.analyte_key;
  }

  formatDateLabel(value: string | null): string {
    if (!value) {
      return this.copy.unknownDate;
    }
    const ts = Date.parse(value);
    if (!Number.isFinite(ts)) {
      return this.copy.unknownDate;
    }
    return format(new Date(ts), 'dd.MM.yyyy HH:mm');
  }

  formatLastValue(item: V2AnalyteItemResponse): string {
    if (item.last_value_numeric !== null && item.last_value_numeric !== undefined) {
      return `${this.formatNumeric(item.last_value_numeric)}${item.unit ? ` ${item.unit}` : ''}`;
    }
    if (item.last_value_text) {
      return item.last_value_text;
    }
    return this.copy.unknownValue;
  }

  trackByAnalyte(_: number, item: V2AnalyteItemResponse): string {
    return item.analyte_key;
  }

  private loadAnalytes(): void {
    this.isLoadingAnalytes = true;
    this.v2Service.getAnalytes().subscribe({
      next: (rows) => {
        this.analytes = rows ?? [];
        this.refreshVisibleAnalytes();
        this.isLoadingAnalytes = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? this.copy.loadAnalytesFailed;
        this.isLoadingAnalytes = false;
      },
    });
  }

  private setFile(file: File): void {
    this.selectedFile = file;
    this.errorMessage = '';
    this.uploadMessage = '';
  }

  private refreshVisibleAnalytes(): void {
    const term = this.searchTerm.trim().toLowerCase();

    const filtered = this.analytes.filter((item) => {
      if (this.numericOnly && item.last_value_numeric === null) {
        return false;
      }
      if (this.textOnly && !item.last_value_text) {
        return false;
      }
      if (!term) {
        return true;
      }
      const haystack = [
        this.getPrimaryLabel(item),
        item.analyte_key,
        item.raw_name ?? '',
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(term);
    });

    filtered.sort((left, right) => this.compareAnalytes(left, right));
    this.visibleAnalytes = filtered;
  }

  private compareAnalytes(left: V2AnalyteItemResponse, right: V2AnalyteItemResponse): number {
    if (this.sortMode === 'recent') {
      const leftTs = this.timestampOrZero(left.last_date);
      const rightTs = this.timestampOrZero(right.last_date);
      if (leftTs !== rightTs) {
        return rightTs - leftTs;
      }
      return this.getPrimaryLabel(left).localeCompare(this.getPrimaryLabel(right), undefined, {
        sensitivity: 'base',
      });
    }

    const byName = this.getPrimaryLabel(left).localeCompare(this.getPrimaryLabel(right), undefined, {
      sensitivity: 'base',
    });
    return this.sortMode === 'az' ? byName : -byName;
  }

  private timestampOrZero(value: string | null): number {
    if (!value) {
      return 0;
    }
    const ts = Date.parse(value);
    return Number.isFinite(ts) ? ts : 0;
  }

  private formatNumeric(value: number): string {
    if (!Number.isFinite(value)) {
      return this.copy.unknownValue;
    }
    if (Number.isInteger(value)) {
      return String(value);
    }
    return value.toFixed(2).replace(/\.?0+$/, '');
  }

  private loadLanguage(): V2DashboardLang {
    const stored = localStorage.getItem(this.langStorageKey);
    return stored === 'es' || stored === 'en' ? stored : 'es';
  }

  private formatUploadMessage(response: V2UploadResponse): string {
    if ('status' in response && response.status === 'duplicate') {
      return `${this.copy.duplicatePrefix} ${response.document_id}.`;
    }
    return `${this.copy.processedPrefix} ${response.num_metrics}.`;
  }
}
