import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { V2DocumentListItemResponse } from '../../../../core/models/v2.model';
import { AuthService } from '../../../../core/services/auth.service';
import { LanguageService } from '../../../../core/services/language.service';
import { ThemeService } from '../../../../core/services/theme.service';
import { V2Service } from '../../../../core/services/v2.service';

@Component({
  selector: 'app-patient-profile-page',
  standalone: false,
  templateUrl: './profile-page.component.html',
  styleUrls: ['./profile-page.component.scss'],
})
export class PatientProfilePageComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly themeService = inject(ThemeService);
  private readonly fb = inject(FormBuilder);
  private readonly languageService = inject(LanguageService);
  private readonly v2Service = inject(V2Service);
  private readonly destroyRef = inject(DestroyRef);
  readonly user = this.auth.user;
  readonly theme = this.themeService.theme;
  currentLang = this.languageService.currentLang;

  readonly nameForm = this.fb.nonNullable.group({
    full_name: [this.user()?.full_name ?? '', [Validators.required, Validators.minLength(2)]],
  });
  savingName = false;
  nameMessage = '';
  nameError = '';
  documents: V2DocumentListItemResponse[] = [];
  documentsLoading = false;
  documentsError = '';
  documentsMessage = '';
  deletingDocumentId: string | null = null;

  constructor() {
    this.languageService
      .onLangChange()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((lang) => {
        this.currentLang = lang;
      });
  }

  ngOnInit(): void {
    this.loadDocuments();
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  setTheme(theme: 'dark' | 'light'): void {
    this.themeService.setTheme(theme);
  }

  setLanguage(lang: string): void {
    this.languageService.setLanguage(lang);
    this.currentLang = this.languageService.currentLang;
  }

  saveName(): void {
    if (this.nameForm.invalid) {
      this.nameForm.markAllAsTouched();
      return;
    }
    this.savingName = true;
    this.nameMessage = '';
    this.nameError = '';
    const { full_name } = this.nameForm.getRawValue();
    this.auth.updateProfile({ full_name }).subscribe({
      next: () => {
        this.savingName = false;
        this.nameMessage = 'profile.nameSaved';
      },
      error: (err) => {
        this.nameError = err?.error?.detail ?? 'Failed to update name.';
        this.savingName = false;
      },
    });
  }

  loadDocuments(): void {
    this.documentsLoading = true;
    this.documentsError = '';
    this.documentsMessage = '';
    this.v2Service.listDocuments().subscribe({
      next: (docs) => {
        this.documents = docs ?? [];
        this.documentsLoading = false;
      },
      error: (err) => {
        this.documentsError = err?.error?.detail ?? this.text('loadError');
        this.documentsLoading = false;
      },
    });
  }

  deleteDocument(document: V2DocumentListItemResponse): void {
    if (this.deletingDocumentId) {
      return;
    }
    const confirmText = this.text('confirmDelete');
    if (!window.confirm(confirmText)) {
      return;
    }
    this.deletingDocumentId = document.id;
    this.documentsError = '';
    this.documentsMessage = '';
    this.v2Service.deleteDocument(document.id).subscribe({
      next: () => {
        this.documents = this.documents.filter((item) => item.id !== document.id);
        this.documentsMessage = this.text('deletedOk');
        this.deletingDocumentId = null;
      },
      error: (err) => {
        this.documentsError = err?.error?.detail ?? this.text('deleteError');
        this.deletingDocumentId = null;
      },
    });
  }

  documentDate(document: V2DocumentListItemResponse): string {
    return document.analysis_date || document.report_date || document.created_at || '';
  }

  documentName(document: V2DocumentListItemResponse): string {
    return document.source_filename?.trim() || `${this.text('documentFallback')} ${document.id.slice(0, 8)}`;
  }

  documentsHeading(): string {
    return this.currentLang === 'es' ? 'Documentos cargados' : 'Uploaded documents';
  }

  documentsSubtitle(): string {
    return this.currentLang === 'es'
      ? 'Puedes eliminar un documento si se procesó mal o quieres reemplazarlo.'
      : 'You can delete a document if it was parsed incorrectly or you want to replace it.';
  }

  private text(
    key:
      | 'confirmDelete'
      | 'deletedOk'
      | 'deleteError'
      | 'loadError'
      | 'documentFallback',
  ): string {
    const isEs = this.currentLang === 'es';
    const messages = {
      confirmDelete: isEs ? '¿Eliminar este documento y todas sus métricas?' : 'Delete this document and all its metrics?',
      deletedOk: isEs ? 'Documento eliminado.' : 'Document deleted.',
      deleteError: isEs ? 'No se pudo eliminar el documento.' : 'Failed to delete document.',
      loadError: isEs ? 'No se pudieron cargar los documentos.' : 'Failed to load documents.',
      documentFallback: isEs ? 'Documento' : 'Document',
    } as const;
    return messages[key];
  }
}
