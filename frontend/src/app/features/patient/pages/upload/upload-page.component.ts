import { Component, inject } from "@angular/core";
import { TranslateService } from "@ngx-translate/core";

import { V2Service } from "../../../../core/services/v2.service";
import { V2UploadResponse } from "../../../../core/models/v2.model";
import { getV2UiStrings } from "../../../v2/i18n/v2-ui-strings";

@Component({
  selector: "app-patient-upload-page",
  standalone: false,
  templateUrl: "./upload-page.component.html",
  styleUrls: ["./upload-page.component.scss"],
})
export class PatientUploadPageComponent {
  private readonly v2Service = inject(V2Service);
  private readonly translate = inject(TranslateService);

  selectedFile: File | null = null;
  isUploading = false;
  uploadMessage = "";
  errorMessage = "";
  isDragging = false;

  get uploadAccuracyHint(): string {
    return getV2UiStrings().uploadAccuracyHint;
  }

  onFileSelected(event: Event): void {
    if (this.isUploading) {
      return;
    }
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
    if (this.isUploading) {
      return;
    }
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
    if (this.isUploading) {
      return;
    }
    this.selectedFile = null;
    this.uploadMessage = "";
    this.errorMessage = "";
  }

  submit(): void {
    if (this.isUploading) {
      return;
    }
    if (!this.selectedFile) {
      this.errorMessage = this.translate.instant("ERRORS.UPLOAD_FILE_REQUIRED");
      return;
    }

    this.isUploading = true;
    this.uploadMessage = getV2UiStrings().uploadLongRunningStatus;
    this.errorMessage = "";

    this.v2Service.uploadDocument(this.selectedFile).subscribe({
      next: (response: V2UploadResponse) => {
        this.isUploading = false;
        this.uploadMessage = this.formatV2UploadMessage(response);
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

  private formatV2UploadMessage(response: V2UploadResponse): string {
    if ("status" in response && response.status === "duplicate") {
      return `Duplicate document detected. Reused ${response.document_id}.`;
    }
    return `Document processed. Saved ${response.num_metrics} metrics.`;
  }
}
