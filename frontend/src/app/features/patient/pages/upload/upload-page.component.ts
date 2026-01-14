import { Component, inject } from "@angular/core";
import { TranslateService } from "@ngx-translate/core";

import { PatientService } from "../../../../core/services/patient.service";
import { AnalysisSummary } from "../../../../core/models/analysis.model";

@Component({
  selector: "app-patient-upload-page",
  standalone: false,
  templateUrl: "./upload-page.component.html",
  styleUrls: ["./upload-page.component.scss"],
})
export class PatientUploadPageComponent {
  private readonly patientService = inject(PatientService);
  private readonly translate = inject(TranslateService);

  selectedFile: File | null = null;
  isUploading = false;
  uploadMessage = "";
  uploadedAnalysis: AnalysisSummary | null = null;
  errorMessage = "";
  isDragging = false;

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
    if (event.dataTransfer?.files?.length) {
      const file = Array.from(event.dataTransfer.files).find((f) => f.type === "application/pdf");
      if (file) {
        this.setFile(file);
      } else {
        this.errorMessage = this.translate.instant("ERRORS.UPLOAD_ONLY_PDF");
      }
    }
  }

  clearSelection(): void {
    this.selectedFile = null;
    this.uploadedAnalysis = null;
    this.uploadMessage = "";
    this.errorMessage = "";
  }

  submit(): void {
    if (!this.selectedFile) {
      this.errorMessage = this.translate.instant("ERRORS.UPLOAD_FILE_REQUIRED");
      return;
    }

    this.isUploading = true;
    this.uploadMessage = this.translate.instant("UPLOAD.STATUS_UPLOADING");
    this.errorMessage = "";

    this.patientService.uploadPdf(this.selectedFile).subscribe({
      next: ({ analysis_id }) => {
        this.uploadMessage = this.translate.instant("UPLOAD.STATUS_FETCHING");
        this.fetchAnalysis(analysis_id);
      },
      error: (err) => {
        this.isUploading = false;
        this.errorMessage = err?.error?.detail ?? this.translate.instant("ERRORS.UPLOAD_FAILED");
      },
    });
  }

  private setFile(file: File): void {
    this.selectedFile = file;
    this.uploadMessage = "";
    this.errorMessage = "";
  }

  private fetchAnalysis(analysisId: string): void {
    this.patientService.getAnalyses().subscribe({
      next: (analyses) => {
        this.isUploading = false;
        this.uploadedAnalysis = analyses.find((analysis) => analysis.id === analysisId) ?? null;
        if (!this.uploadedAnalysis) {
          this.uploadMessage = this.translate.instant("UPLOAD.STATUS_SAVED");
        }
      },
      error: () => {
        this.isUploading = false;
        this.uploadMessage = this.translate.instant("UPLOAD.STATUS_SAVED");
      },
    });
  }
}
