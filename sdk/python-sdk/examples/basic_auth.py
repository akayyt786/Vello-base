"""Basic authentication example."""

from ownfirebase import OwnFirebaseConfig, init_ownfirebase

def main():
    config = OwnFirebaseConfig(base_url='http://localhost:8000')
    app = init_ownfirebase(config)
    
    print("Authentication examples:")
    print("1. Register: app.auth.register(email, password)")
    print("2. Login: app.auth.login(email, password)")
    print("3. Refresh: app.auth.refresh_token(refresh_token)")
    print("4. Anonymous: app.auth.anonymous_sign_in()")
    print("5. Magic link: app.auth.send_magic_link(email)")
    print("6. MFA TOTP: app.auth.enroll_totp()")

if __name__ == '__main__':
    main()
