import { OwnFirebaseClient } from './client';
import type { AppCheckToken } from './types';

export class AppCheckSDK extends OwnFirebaseClient {
  /**
   * Exchange a platform attestation (e.g. reCAPTCHA token, DeviceCheck assertion)
   * for an OwnFirebase App Check token. The token must be included in subsequent
   * API requests as the `X-App-Check-Token` header when App Check enforcement
   * is enabled on the project.
   */
  async exchangeToken(options: {
    provider: 'recaptcha_v3' | 'recaptcha_enterprise' | 'device_check' | 'safety_net' | 'debug';
    attestation: string;
  }): Promise<AppCheckToken> {
    return this.request('POST', this.projectUrl('app-check/'), {
      provider: options.provider,
      attestation: options.attestation,
    });
  }
}
