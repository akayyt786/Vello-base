"""Data operations example."""

from ownfirebase import OwnFirebaseConfig, init_ownfirebase

def main():
    config = OwnFirebaseConfig(
        base_url='http://localhost:8000',
        project_id='my-project-123',
    )
    app = init_ownfirebase(config)
    
    print("Data API examples:")
    print("1. Create collection: app.data.create_collection('users')")
    print("2. Create document: app.data.create_document('users', data)")
    print("3. Read document: app.data.get_document('users', doc_id)")
    print("4. Update: app.data.update_document('users', doc_id, data)")
    print("5. List: app.data.list_documents('users')")
    print("6. Delete: app.data.delete_document('users', doc_id)")

if __name__ == '__main__':
    main()
