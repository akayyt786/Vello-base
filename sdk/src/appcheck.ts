import { OwnFirebaseClient } from './client';
import type { AppCheckToken } from './types';

export class AppCheckSDK extends OwnFirebaseClient {
  /**
   * Exchange a platform attestation (e.g. reCAPTCHA token, Play Integrity token,
   * DeviceCheck assertion) for an OwnFirebase App Check token. The token must be
   * included in subsequent API requests as the `X-App-Check-Token` header when
   * App Check enforcement is enabled on the project.
   */
  async exchangeToken(options: {
    provider: 'recaptcha_v3' | 'recaptcha_enterprise' | 'play_integrity' | 'device_check' | 'debug';
    platform: 'web' | 'android' | 'ios';
    rawToken: string;
  }): Promise<AppCheckToken> {
    return this.request('POST', this.projectUrl('app-check/exchange/'), {
      provider: options.provider,
      platform: options.platform,
      raw_token: options.rawToken,
    });
  }
}
