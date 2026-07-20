import json
import logging
import jwt
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"


def verify_google_id_token(id_token):
    """
    Verify Google ID token by calling tokeninfo endpoint.
    Returns dict with sub, email, name, picture on success.
    Returns (None, error_str) on failure.
    """
    try:
        resp = requests.get(GOOGLE_TOKEN_INFO_URL, params={"id_token": id_token}, timeout=5)
        if resp.status_code != 200:
            return None, "Invalid Google ID token."
        data = resp.json()
        # Optionally verify aud matches configured client ID
        expected_aud = getattr(settings, "GOOGLE_CLIENT_ID", None)
        if expected_aud and data.get("aud") != expected_aud:
            return None, "Google token audience mismatch."
        return {
            "provider_uid": data["sub"],
            "email": data.get("email", ""),
            "email_verified": data.get("email_verified", "false") == "true",
            "name": data.get("name", ""),
            "avatar_url": data.get("picture", ""),
            "raw_data": data,
        }, None
    except Exception as exc:
        logger.error("Google token verify failed: %s", exc)
        return None, "Google token verification failed."


def verify_github_access_token(access_token):
    """
    Verify GitHub access token by calling /user endpoint.
    Returns dict with id, email, name, avatar_url on success.
    Returns (None, error_str) on failure.
    """
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(GITHUB_USER_URL, headers=headers, timeout=5)
        if resp.status_code != 200:
            return None, "Invalid GitHub access token."
        user_data = resp.json()
        email = user_data.get("email") or ""
        if not email:
            # Fetch primary verified email
            email_resp = requests.get(GITHUB_EMAIL_URL, headers=headers, timeout=5)
            if email_resp.status_code == 200:
                emails = email_resp.json()
                primary = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                email = primary or ""
        return {
            "provider_uid": str(user_data["id"]),
            "email": email,
            "email_verified": True,
            "name": user_data.get("name") or user_data.get("login", ""),
            "avatar_url": user_data.get("avatar_url", ""),
            "raw_data": user_data,
        }, None
    except Exception as exc:
        logger.error("GitHub token verify failed: %s", exc)
        return None, "GitHub token verification failed."


def verify_apple_id_token(id_token):
    """
    Verify Apple ID token (a JWS signed by Apple) against Apple's published
    JWKS. Returns dict with sub, email on success.
    Returns (None, error_str) on failure.

    Apple ID tokens carry no name/picture claims -- Apple only sends the
    user's name once, out-of-band, on the client during the *first*
    authorization -- so name/avatar_url are always blank here.
    """
    try:
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
        except jwt.InvalidTokenError:
            return None, "Invalid Apple ID token."
        if not kid:
            return None, "Invalid Apple ID token."

        resp = requests.get(APPLE_KEYS_URL, timeout=5)
        if resp.status_code != 200:
            return None, "Could not fetch Apple signing keys."
        jwk = next((k for k in resp.json().get("keys", []) if k.get("kid") == kid), None)
        if not jwk:
            return None, "Invalid Apple ID token."
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

        # Optionally verify aud matches configured client ID (matches
        # verify_google_id_token's expected_aud pattern above).
        expected_aud = getattr(settings, "APPLE_CLIENT_ID", None)
        decode_kwargs = {"algorithms": ["RS256"], "issuer": APPLE_ISSUER}
        if expected_aud:
            decode_kwargs["audience"] = expected_aud
        else:
            decode_kwargs["options"] = {"verify_aud": False}

        data = jwt.decode(id_token, key=public_key, **decode_kwargs)

        email_verified = data.get("email_verified", False)
        if isinstance(email_verified, str):
            email_verified = email_verified.lower() == "true"

        return {
            "provider_uid": data["sub"],
            "email": data.get("email", ""),
            "email_verified": email_verified,
            "name": "",
            "avatar_url": "",
            "raw_data": data,
        }, None
    except jwt.ExpiredSignatureError:
        return None, "Apple ID token has expired."
    except jwt.InvalidTokenError as exc:
        logger.error("Apple token verify failed: %s", exc)
        return None, "Invalid Apple ID token."
    except Exception as exc:
        logger.error("Apple token verify failed: %s", exc)
        return None, "Apple token verification failed."
