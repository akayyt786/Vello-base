# OwnFirebase Python SDK

A Python SDK for **OwnFirebase** — a self-hosted Firebase alternative built on Django + PostgreSQL.

Provides seamless access to all 12 integrated services: authentication, Firestore-like data storage, cloud functions, object storage, push notifications, analytics, remote configuration, A/B testing, error tracking, and more.

---

## Installation

### From PyPI (when published)

```bash
pip install ownfirebase
```

### From source

```bash
git clone https://github.com/akayyt786/ownfirebase.git
cd sdk/python-sdk
pip install -e .
```

### With optional async support

```bash
pip install ownfirebase[async]
```

---

## Quick Start

### 1. Initialize the SDK

```python
from ownfirebase import OwnFirebaseConfig, init_ownfirebase

config = OwnFirebaseConfig(
    base_url='http://localhost:8000',
    project_id='my-project-id',
)
app = init_ownfirebase(config)
```

### 2. Register & Login

```python
# Register a new user
tokens = app.auth.register(
    email='user@example.com',
    password='SecurePass123!'
)

# Or login with existing account
tokens = app.auth.login(
    email='user@example.com',
    password='SecurePass123!'
)

# Propagate token to all services
app.set_access_token(tokens.access)
```

### 3. Use any service

```python
# Create a document
doc = app.data.create_document('users', {
    'name': 'Alice',
    'email': 'alice@example.com',
    'age': 30
})

# Log an analytics event
app.analytics.log_event('purchase', {
    'item_id': 'sku-123',
    'price': 49.99
})

# Send a push notification
app.push.send_to_device('device-token-123', 
    title='Hello Alice!',
    body='Welcome to OwnFirebase'
)
```

---

## Services

### 12 Integrated Services

| Service | Module | Description |
|---------|--------|-------------|
| **Authentication** | `app.auth` | Registration, login, MFA, magic links, social auth |
| **Data** | `app.data` | Firestore-like collections and documents |
| **Storage** | `app.storage` | S3-compatible object storage with presigned URLs |
| **Cloud Functions** | `app.functions` | Deploy and invoke HTTP/background functions |
| **Realtime** | `app.realtime` | WebSocket listeners for document changes (stub) |
| **Analytics** | `app.analytics` | Event tracking, user properties, aggregated queries |
| **Remote Config** | `app.remote_config` | Configuration parameters with conditional overrides |
| **A/B Testing** | `app.abtesting` | Experiments with variant assignment and analytics |
| **Crashlytics** | `app.crashlytics` | Crash reporting, error grouping, performance traces |
| **Push Notifications** | `app.push` | Device tokens, topics, campaigns |
| **Projects** | `app.projects` | Project CRUD and membership management |
| **App Check** | `app.appcheck` | App attestation and device verification |

---

### Authentication (`app.auth`)

```python
# Register
tokens = app.auth.register(email='user@example.com', password='pass123')

# Login
tokens = app.auth.login(email='user@example.com', password='pass123')

# Refresh token
new_tokens = app.auth.refresh_token(tokens.refresh)

# Anonymous signin
anon = app.auth.anonymous_sign_in()

# TOTP MFA
totp_data = app.auth.enroll_totp()
app.auth.confirm_totp(code='123456')

# Magic link
app.auth.send_magic_link('user@example.com')
tokens = app.auth.verify_magic_link(token)

# Social auth
tokens = app.auth.google_sign_in(id_token)
```

### Data (`app.data`)

```python
# Create collection
coll = app.data.create_collection('users')

# Create document (auto-generates ID)
doc = app.data.create_document('users', {
    'name': 'Alice', 'age': 30
})

# Read document
doc = app.data.get_document('users', doc_id)

# Update (partial)
doc = app.data.update_document('users', doc_id, {'age': 31})

# Replace (full)
doc = app.data.replace_document('users', doc_id, {'name': 'Alice', 'age': 31})

# List
response = app.data.list_documents('users')

# Delete
app.data.delete_document('users', doc_id)

# Batch operations
from ownfirebase import WriteBatchOperation
ops = [
    WriteBatchOperation(op='set', collection='users', doc_id='u1', data={...}),
    WriteBatchOperation(op='update', collection='users', doc_id='u2', data={...}),
]
result = app.data.write_batch(ops)
```

### Storage (`app.storage`)

```python
# Upload
obj = app.storage.upload_file(file_path, content_type='text/plain')

# Download
contents = app.storage.download_file(file_id)

# Presigned URLs
url_data = app.storage.get_presigned_upload_url(filename, expires_in_seconds=3600)
url_data = app.storage.get_presigned_download_url(file_id, expires_in_seconds=3600)

# List & delete
files = app.storage.list_files()
app.storage.delete_file(file_id)
```

### Cloud Functions (`app.functions`)

```python
# List functions
functions = app.functions.list_functions()

# Create function
func = app.functions.create_function(
    name='send-email',
    runtime='python3.11',
    entry_point='main',
    source_code='def main(event): ...'
)

# Invoke
result = app.functions.invoke_function(func.id, data={...})

# Logs
logs = app.functions.get_function_logs(function_id)
```

### Analytics (`app.analytics`)

```python
# Log event
event = app.analytics.log_event(
    event_name='purchase',
    event_params={'item_id': 'sku-123', 'price': 49.99},
    platform='web'
)

# Batch log
result = app.analytics.batch_log_events([
    {'event_name': 'page_view', ...},
    {'event_name': 'button_click', ...},
])

# User properties
app.analytics.set_user_properties('user-123', {
    'plan': 'pro', 'country': 'US'
})

# Query
result = app.analytics.query_analytics(
    metric='event_count',
    start_date='2024-01-01',
    end_date='2024-01-31',
    group_by='day'
)
```

### Remote Config (`app.remote_config`)

```python
# Fetch evaluated config
config = app.remote_config.fetch_evaluated_config(
    platform='web',
    app_version='1.2.3'
)

# Create parameter
param = app.remote_config.create_parameter(
    key='feature_flag_new_ui',
    default_value='false',
    value_type='boolean'
)

# Add condition for override
cond = app.remote_config.add_condition(
    parameter_id=param.id,
    name='ios_only',
    expression="platform == 'ios'",
    value='true'
)
```

### A/B Testing (`app.abtesting`)

```python
# Create experiment
exp = app.abtesting.create_experiment(
    name='homepage_redesign'
)

# Add variants
app.abtesting.add_variant(exp.id, name='control', allocation=50)
app.abtesting.add_variant(exp.id, name='variant_a', allocation=50)

# Start
exp = app.abtesting.start_experiment(exp.id)

# Assign user to variant
assignment = app.abtesting.assign_user_to_variant(exp.id, user_id)

# Record conversion
app.abtesting.record_conversion(exp.id, user_id, conversion_value=49.99)
```

### Push Notifications (`app.push`)

```python
# Register device
token = app.push.register_token(
    token='fcm-token-abc123',
    platform='web'
)

# Create topic
topic = app.push.create_topic('promotions')

# Subscribe device
app.push.subscribe_to_topic(topic.id, token.id)

# Send notification
result = app.push.send_to_device(
    token_id=token.id,
    title='Hello!',
    body='This is a notification'
)

# Send to topic
result = app.push.send_to_topic(topic.id, title='Sale', body='50% off!')
```

### Crashlytics (`app.crashlytics`)

```python
# Report crash
crash = app.crashlytics.report_crash(
    exception_type='NullPointerException',
    message='Attempt to read field on null',
    stack_trace='...',
    app_version='1.0.0',
    platform='android',
    fatal=True
)

# Performance trace
trace = app.crashlytics.submit_performance_trace(
    name='app_startup',
    duration_ms=1250,
    attributes={'device': 'iPhone 14'}
)

# Network request
app.crashlytics.submit_network_request(
    url='https://api.example.com/data',
    method='GET',
    status_code=200,
    duration_ms=145,
    request_size=256,
    response_size=1024
)
```

---

## Error Handling

All methods raise `APIError` on non-2xx responses:

```python
from ownfirebase import APIError

try:
    doc = app.data.get_document('users', 'nonexistent-id')
except APIError as e:
    print(f"Status: {e.status}")
    print(f"Message: {e.message}")
    print(f"Detail: {e.detail}")
```

---

## Development

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/ -v
pytest tests/ --cov=ownfirebase
```

### Format & lint

```bash
black ownfirebase/ examples/ tests/
isort ownfirebase/ examples/ tests/
flake8 ownfirebase/
mypy ownfirebase/
```

### Build

```bash
python -m build
python -m twine upload dist/*
```

---

## Examples

See `examples/` directory:
- `basic_auth.py` — Authentication flows
- `data_operations.py` — CRUD and batch operations
- `full_example.py` — End-to-end walkthrough

---

## License

MIT — see LICENSE file.

---

## Links

- **Repository**: https://github.com/akayyt786/ownfirebase
- **Issues**: https://github.com/akayyt786/ownfirebase/issues
- **Documentation**: https://github.com/akayyt786/ownfirebase#readme
