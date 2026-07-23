import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleIdentitySdk {
  accounts: {
    id: {
      initialize(options: {
        client_id: string;
        callback: (response: GoogleCredentialResponse) => void;
      }): void;
      renderButton(
        element: HTMLElement,
        options: {
          type: 'standard';
          theme: 'outline';
          size: 'large';
          text: 'continue_with';
          shape: 'rectangular';
          logo_alignment: 'left';
          width: number;
          locale: string;
        },
      ): void;
    };
  };
}

interface FacebookLoginResponse {
  status?: string;
  authResponse?: {
    accessToken?: string;
  };
}

interface FacebookSdk {
  init(options: {
    appId: string;
    cookie: boolean;
    xfbml: boolean;
    version: string;
  }): void;
  login(
    callback: (response: FacebookLoginResponse) => void,
    options: { scope: string; return_scopes: boolean },
  ): void;
}

declare global {
  interface Window {
    google?: GoogleIdentitySdk;
    FB?: FacebookSdk;
  }
}

@Injectable({ providedIn: 'root' })
export class SocialAuthSdkService {
  private readonly document = inject(DOCUMENT);
  private facebookInitialization?: Promise<void>;

  async renderGoogleButton(
    element: HTMLElement,
    clientId: string,
    onCredential: (credential: string) => void,
  ): Promise<void> {
    await this.loadScript(
      'nephroai-google-identity',
      'https://accounts.google.com/gsi/client?hl=es',
    );
    const sdk = window.google;
    if (!sdk) {
      throw new Error('Google Identity Services SDK unavailable');
    }

    sdk.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => {
        if (response.credential) {
          onCredential(response.credential);
        }
      },
    });
    element.replaceChildren();
    sdk.accounts.id.renderButton(element, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      text: 'continue_with',
      shape: 'rectangular',
      logo_alignment: 'left',
      width: Math.max(240, Math.min(400, element.clientWidth || 400)),
      locale: 'es',
    });
  }

  initializeFacebook(appId: string, apiVersion: string): Promise<void> {
    if (!this.facebookInitialization) {
      this.facebookInitialization = this.loadScript(
        'nephroai-facebook-sdk',
        'https://connect.facebook.net/es_LA/sdk.js',
      ).then(() => {
        const sdk = window.FB;
        if (!sdk) {
          throw new Error('Facebook SDK unavailable');
        }
        sdk.init({
          appId,
          cookie: false,
          xfbml: false,
          version: apiVersion,
        });
      });
    }
    return this.facebookInitialization;
  }

  loginWithFacebook(): Promise<string | null> {
    const sdk = window.FB;
    if (!sdk) {
      return Promise.reject(new Error('Facebook SDK unavailable'));
    }
    return new Promise((resolve) => {
      sdk.login(
        (response) => {
          resolve(
            response.status === 'connected' && response.authResponse?.accessToken
              ? response.authResponse.accessToken
              : null,
          );
        },
        { scope: 'public_profile,email', return_scopes: true },
      );
    });
  }

  private loadScript(id: string, src: string): Promise<void> {
    const existing = this.document.getElementById(id) as HTMLScriptElement | null;
    if (existing?.dataset['loaded'] === 'true') {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const script = existing ?? this.document.createElement('script');
      script.addEventListener(
        'load',
        () => {
          script.dataset['loaded'] = 'true';
          resolve();
        },
        { once: true },
      );
      script.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), {
        once: true,
      });
      if (!existing) {
        script.id = id;
        script.src = src;
        script.async = true;
        script.defer = true;
        this.document.head.appendChild(script);
      }
    });
  }
}
