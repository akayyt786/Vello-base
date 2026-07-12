"""Comprehensive end-to-end example."""

from ownfirebase import OwnFirebaseConfig, init_ownfirebase

def main():
    app = init_ownfirebase(OwnFirebaseConfig(base_url='http://localhost:8000'))
    print("OwnFirebase Python SDK - Full Example")
    print("=" * 70)
    print("\nServices available:")
    print("  - app.auth: Authentication")
    print("  - app.data: Firestore-like data storage")
    print("  - app.storage: S3-compatible file storage")
    print("  - app.functions: Cloud functions")
    print("  - app.analytics: Event tracking")
    print("  - app.remote_config: Configuration management")
    print("  - app.crashlytics: Error tracking")
    print("  - app.abtesting: A/B experiments")
    print("  - app.push: Push notifications")
    print("  - app.projects: Project management")
    print("\nSee examples/ directory for more...")

if __name__ == '__main__':
    main()
