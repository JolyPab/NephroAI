import { Component, OnInit, inject } from "@angular/core";
import { Router } from "@angular/router";
import { TranslateService } from "@ngx-translate/core";

import { V2Service } from "../../../../core/services/v2.service";
import { V2UploadResponse } from "../../../../core/models/v2.model";
import { getV2UiStrings } from "../../../v2/i18n/v2-ui-strings";
import { BillingService } from "../../../../core/services/billing.service";

@Component({
  selector: "app-patient-upload-page",
  standalone: false,
  templateUrl: "./upload-page.component.html",
  styleUrls: ["./upload-page.component.scss"],
})
export class PatientUploadPageComponent implements OnInit {
  private readonly v2Service = inject(V2Service);
  private readonly translate = inject(TranslateService);
  private readonly router = inject(Router);
  private readonly billingService = inject(BillingService);

  selectedFile: File | null = null;
  isUploading = false;
  uploadMessage = "";
  errorMessage = "";
  showSubscriptionCta = false;
  isDragging = false;
  pdfPassword = "";
  passwordRequired = false;
  freeUploadsLimit = 2;
  freeUploadsRemaining: number | null = null;
  canUpload = true;
  hasSubscriptionAccess = false;

  ngOnInit(): void {
    this.loadUploadAllowance();
  }

  get uploadAllowanceText(): string {
    if (this.hasSubscriptionAccess) {
      return "Tu plan incluye cargas de documentos sin límite.";
    }
    if (this.freeUploadsRemaining === null) {
      return "Puedes cargar 2 documentos gratis, sin tarjeta.";
    }
    if (this.freeUploadsRemaining === 1) {
      return "Te queda 1 carga gratuita, sin tarjeta.";
    }
    if (this.freeUploadsRemaining > 1) {
      return `Tienes ${this.freeUploadsRemaining} cargas gratuitas, sin tarjeta.`;
    }
    return `Ya usaste tus ${this.freeUploadsLimit} cargas gratuitas.`;
  }

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
    if (this.isUploading || !this.canUpload) {
      return;
    }
    if (!this.selectedFile) {
      this.errorMessage = this.translate.instant("ERRORS.UPLOAD_FILE_REQUIRED");
      return;
    }

    this.isUploading = true;
    this.uploadMessage = getV2UiStrings().uploadLongRunningStatus;
    this.errorMessage = "";

    this.v2Service.uploadDocument(this.selectedFile, this.pdfPassword.trim()).subscribe({
      next: (response: V2UploadResponse) => {
        this.isUploading = false;
        this.showSubscriptionCta = false;
        this.passwordRequired = false;
        this.pdfPassword = "";
        if (typeof response.free_uploads_remaining === "number") {
          this.freeUploadsRemaining = response.free_uploads_remaining;
          this.canUpload = this.hasSubscriptionAccess || response.free_uploads_remaining > 0;
        }
        this.uploadMessage = this.formatV2UploadMessage(response);
      },
      error: (err) => {
        this.isUploading = false;
        const uploadError = this.parseUploadError(err);
        this.errorMessage = uploadError.message;
        this.passwordRequired = uploadError.requiresPassword;
        if (uploadError.requiresPassword && uploadError.code === "pdf_password_invalid") {
          this.pdfPassword = "";
        }
        this.showSubscriptionCta =
          err?.status === 403 &&
          (uploadError.code === "free_upload_limit_reached" || this.isSubscriptionError(this.errorMessage));
        if (uploadError.code === "free_upload_limit_reached") {
          this.freeUploadsRemaining = 0;
          this.canUpload = false;
        }
      },
    });
  }

  goToSubscription(): void {
    void this.router.navigate(["/patient/profile"]);
  }

  private setFile(file: File): void {
    this.selectedFile = file;
    this.uploadMessage = "";
    this.errorMessage = "";
    this.showSubscriptionCta = false;
    this.passwordRequired = false;
    this.pdfPassword = "";
  }

  private loadUploadAllowance(): void {
    this.billingService.getSubscription().subscribe({
      next: (subscription) => {
        this.hasSubscriptionAccess = ["active", "trialing"].includes(subscription.status);
        this.freeUploadsLimit = subscription.free_uploads_limit;
        this.freeUploadsRemaining = subscription.free_uploads_remaining;
        this.canUpload = subscription.can_upload;
      },
      error: () => undefined,
    });
  }

  private formatV2UploadMessage(response: V2UploadResponse): string {
    if ("status" in response && response.status === "duplicate") {
      return "Este documento ya estaba cargado. Conservamos sus métricas existentes.";
    }
    return `Documento procesado. Se guardaron ${response.num_metrics} métricas.`;
  }

  private isSubscriptionError(message: string): boolean {
    return message.toLowerCase().includes("suscrip");
  }

  private parseUploadError(err: any): { code: string; message: string; requiresPassword: boolean } {
    const detail = err?.error?.detail;
    if (
      detail?.code === "pdf_password_required" ||
      detail?.code === "pdf_password_invalid" ||
      detail?.code === "free_upload_limit_reached"
    ) {
      return {
        code: detail.code,
        message: detail.message,
        requiresPassword:
          detail.code === "pdf_password_required" || detail.code === "pdf_password_invalid",
      };
    }
    return {
      code: "",
      message: typeof detail === "string" ? detail : this.translate.instant("ERRORS.UPLOAD_FAILED"),
      requiresPassword: false,
    };
  }
}
