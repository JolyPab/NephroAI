import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { format } from 'date-fns';

import { V2DoctorNoteResponse, V2SeriesPointResponse } from '../../../../core/models/v2.model';
import { V2DashboardLang } from '../../i18n/analyte-display';

interface PanelCopy {
  dateLabel: string;
  valueLabel: string;
  statusLabel: string;
  pageLabel: string;
  evidenceLabel: string;
  doctorNotesLabel: string;
  doctorFallback: string;
  emptyNotes: string;
}

const PANEL_COPY: Record<V2DashboardLang, PanelCopy> = {
  en: {
    dateLabel: 'Date',
    valueLabel: 'Value',
    statusLabel: 'Status',
    pageLabel: 'Page',
    evidenceLabel: 'Evidence',
    doctorNotesLabel: 'Doctor notes',
    doctorFallback: 'Doctor',
    emptyNotes: 'No doctor notes for this point.',
  },
  es: {
    dateLabel: 'Fecha',
    valueLabel: 'Valor',
    statusLabel: 'Estado',
    pageLabel: 'Página',
    evidenceLabel: 'Evidencia',
    doctorNotesLabel: 'Notas del médico',
    doctorFallback: 'Médico',
    emptyNotes: 'No hay notas del médico para este punto.',
  },
};

@Component({
  selector: 'app-v2-point-detail-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './v2-point-detail-panel.component.html',
  styleUrls: ['./v2-point-detail-panel.component.scss'],
})
export class V2PointDetailPanelComponent {
  @Input() open = false;
  @Input() analyteLabel = '';
  @Input() analyteKey = '';
  @Input() unit: string | null = null;
  @Input() point: V2SeriesPointResponse | null = null;
  @Input() valueLabel: string | null = null;
  @Input() statusLabel: string | null = null;
  @Input() doctorNotes: V2DoctorNoteResponse[] = [];
  @Input() language: V2DashboardLang = 'es';

  /** @deprecated pass language instead */
  @Input() emptyDoctorNotesLabel: string | null = null;

  get copy(): PanelCopy {
    return PANEL_COPY[this.language];
  }

  get resolvedEmptyDoctorNotesLabel(): string {
    return this.emptyDoctorNotesLabel ?? this.copy.emptyNotes;
  }

  @Output() closePanel = new EventEmitter<void>();

  close(): void {
    this.closePanel.emit();
  }

  formatDate(value: string | null): string {
    if (!value) {
      return '-';
    }
    const ts = Date.parse(value);
    if (!Number.isFinite(ts)) {
      return '-';
    }
    return format(new Date(ts), 'dd.MM.yyyy HH:mm');
  }

  formatValue(point: V2SeriesPointResponse | null): string {
    if (this.valueLabel) {
      return this.valueLabel;
    }
    if (!point) {
      return '-';
    }
    if (point.y !== null && point.y !== undefined) {
      return `${this.formatNumeric(point.y)}${this.unit ? ` ${this.unit}` : ''}`;
    }
    if (point.text?.trim()) {
      return point.text;
    }
    return '-';
  }

  private formatNumeric(value: number): string {
    if (!Number.isFinite(value)) {
      return '-';
    }
    if (Number.isInteger(value)) {
      return String(value);
    }
    return value.toFixed(2).replace(/\.?0+$/, '');
  }
}
