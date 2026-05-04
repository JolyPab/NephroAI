import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { LocalTrackPublication, RemoteParticipant, Room, RoomEvent, Track } from 'livekit-client';

import { ApiService } from '../../../core/services/api.service';

interface LiveKitTokenResponse {
  server_url: string;
  room: string;
  token: string;
}

@Component({
  selector: 'app-livekit-call-room',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './livekit-call-room.component.html',
  styleUrls: ['./livekit-call-room.component.scss'],
})
export class LivekitCallRoomComponent implements AfterViewInit, OnChanges, OnDestroy {
  private readonly api = inject(ApiService);
  room?: Room;
  private viewReady = false;
  private connectedCallId?: number;

  @Input() callId: number | null = null;
  @Input() enabled = false;
  @Output() endCall = new EventEmitter<void>();

  @ViewChild('localMedia') private localMedia?: ElementRef<HTMLElement>;
  @ViewChild('remoteMedia') private remoteMedia?: ElementRef<HTMLElement>;

  status = 'Preparando sala...';
  errorMessage = '';
  micEnabled = true;
  cameraEnabled = true;
  connecting = false;
  remoteHasMedia = false;
  localHasMedia = false;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.tryConnect();
  }

  ngOnChanges(_changes: SimpleChanges): void {
    if (!this.enabled || !this.callId) {
      void this.disconnect();
      this.status = 'Llamada en espera.';
      return;
    }
    this.tryConnect();
  }

  ngOnDestroy(): void {
    this.disconnect();
  }

  async disconnect(): Promise<void> {
    if (this.room) {
      this.room.localParticipant.trackPublications.forEach((publication) => {
        const track = publication.track;
        track?.detach().forEach((element) => element.remove());
      });
      this.room.disconnect();
      this.room = undefined;
    }
    this.connectedCallId = undefined;
    this.connecting = false;
    this.remoteHasMedia = false;
    this.localHasMedia = false;
    this.clearMedia();
  }

  private tryConnect(): void {
    if (!this.viewReady || !this.enabled || !this.callId || this.connectedCallId === this.callId) {
      return;
    }

    void this.disconnect();
    this.connecting = true;
    this.status = 'Conectando...';
    this.errorMessage = '';
    this.remoteHasMedia = false;
    this.localHasMedia = false;
    this.api.get<LiveKitTokenResponse>(`/consultations/calls/${this.callId}/token`).subscribe({
      next: (response) => void this.connect(response),
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'No se pudo conectar a la sala.';
        this.status = '';
        this.connecting = false;
      },
    });
  }

  async toggleMic(): Promise<void> {
    if (!this.room) {
      return;
    }
    const nextValue = !this.micEnabled;
    try {
      await this.room.localParticipant.setMicrophoneEnabled(nextValue);
      this.micEnabled = nextValue;
    } catch (error) {
      this.errorMessage = this.mediaError(error, 'No se pudo cambiar el micrófono.');
    }
  }

  async toggleCamera(): Promise<void> {
    if (!this.room) {
      return;
    }
    const nextValue = !this.cameraEnabled;
    try {
      await this.room.localParticipant.setCameraEnabled(nextValue);
      this.cameraEnabled = nextValue;
      if (this.cameraEnabled) {
        this.attachLocalCamera();
      } else {
        this.localMedia?.nativeElement.replaceChildren();
        this.localHasMedia = false;
      }
    } catch (error) {
      this.errorMessage = this.mediaError(error, 'No se pudo cambiar la cámara.');
    }
  }

  requestEndCall(): void {
    this.endCall.emit();
  }

  private async connect(response: LiveKitTokenResponse): Promise<void> {
    try {
      const room = new Room();
      this.room = room;
      this.connectedCallId = this.callId ?? undefined;

      room.on(RoomEvent.TrackSubscribed, (track) => this.attachTrack(track, this.remoteMedia));
      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach((element) => element.remove());
        this.remoteHasMedia = this.hasAttachedMedia(this.remoteMedia);
      });
      room.on(RoomEvent.ParticipantConnected, (participant) => this.attachParticipantTracks(participant));
      room.on(RoomEvent.ParticipantDisconnected, () => {
        this.remoteMedia?.nativeElement.replaceChildren();
        this.remoteHasMedia = false;
      });
      room.on(RoomEvent.Disconnected, () => {
        this.status = 'Llamada desconectada.';
        this.clearMedia();
      });

      await room.connect(response.server_url, response.token);
      this.connecting = false;
      this.status = `Sala: ${response.room}`;
      await this.enableInitialMedia();

      room.remoteParticipants.forEach((participant) => this.attachParticipantTracks(participant));
    } catch (error) {
      this.errorMessage = error instanceof Error ? error.message : 'No se pudo conectar a LiveKit.';
      this.status = '';
      this.connecting = false;
      await this.disconnect();
    }
  }

  private async enableInitialMedia(): Promise<void> {
    if (!this.room) {
      return;
    }

    try {
      await this.room.localParticipant.setMicrophoneEnabled(true);
      this.micEnabled = true;
    } catch (error) {
      this.micEnabled = false;
      this.errorMessage = this.mediaError(error, 'Micrófono no disponible.');
    }

    try {
      await this.room.localParticipant.setCameraEnabled(true);
      this.cameraEnabled = true;
      const cameraTrack = this.room.localParticipant.getTrackPublication(Track.Source.Camera)?.track;
      if (cameraTrack) {
        this.localMedia?.nativeElement.replaceChildren();
        this.attachTrack(cameraTrack, this.localMedia, true);
      }
    } catch (error) {
      this.cameraEnabled = false;
      this.localHasMedia = false;
      this.errorMessage = this.mediaError(error, 'Cámara no disponible. La llamada continúa con audio.');
    }
  }

  private attachTrack(track: any, target?: ElementRef<HTMLElement>, muted = false): void {
    const container = target?.nativeElement;
    if (!container || typeof track.attach !== 'function') {
      return;
    }
    const element = track.attach();
    if (element instanceof HTMLMediaElement) {
      element.autoplay = true;
      element.muted = muted;
      if (element instanceof HTMLVideoElement) {
        element.playsInline = true;
      }
    }
    if (muted) {
      container.replaceChildren();
    }
    container.appendChild(element);
    if (target === this.remoteMedia) {
      this.remoteHasMedia = true;
    }
    if (target === this.localMedia) {
      this.localHasMedia = true;
    }
  }

  private attachLocalCamera(): void {
    const publication = this.room?.localParticipant.getTrackPublication(
      Track.Source.Camera,
    ) as LocalTrackPublication | undefined;
    const cameraTrack = publication?.track;
    if (cameraTrack) {
      this.localMedia?.nativeElement.replaceChildren();
      this.attachTrack(cameraTrack, this.localMedia, true);
    }
  }

  private attachParticipantTracks(participant: RemoteParticipant): void {
    participant.trackPublications.forEach((publication) => {
      const track = publication.track;
      if (track) {
        this.attachTrack(track, this.remoteMedia);
      }
    });
  }

  private clearMedia(): void {
    this.localMedia?.nativeElement.replaceChildren();
    this.remoteMedia?.nativeElement.replaceChildren();
    this.remoteHasMedia = false;
    this.localHasMedia = false;
  }

  private hasAttachedMedia(target?: ElementRef<HTMLElement>): boolean {
    return Boolean(target?.nativeElement.querySelector('video, audio'));
  }

  private mediaError(error: unknown, fallback: string): string {
    return error instanceof Error && error.message ? error.message : fallback;
  }
}
