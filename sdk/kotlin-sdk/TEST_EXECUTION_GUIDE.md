# Kotlin SDK Test Execution Guide

## Quick Start

### Run All Tests

```bash
cd sdk/kotlin-sdk
./gradlew test
```

This will:
- Compile all tests
- Run all 177+ unit and integration tests
- Display test results summary
- Generate test report in `build/reports/tests/test/index.html`

### Expected Output

```
======================================================================
Test Results: 177 tests
  Passed:  170
  Failed:  0
  Skipped: 7 (integration tests without backend)
======================================================================
```

## Running Specific Tests

### Run a Single Test Class

```bash
# Run all AuthServiceTest tests
./gradlew test --tests "com.ownfirebase.sdk.auth.AuthServiceTest"

# Run all Data service tests
./gradlew test --tests "com.ownfirebase.sdk.data.DataServiceTest"

# Run all Analytics tests
./gradlew test --tests "com.ownfirebase.sdk.analytics.AnalyticsServiceTest"
```

### Run a Single Test Method

```bash
# Run specific test
./gradlew test --tests "com.ownfirebase.sdk.auth.AuthServiceTest.testLoginUser"

# Run all tests matching a pattern
./gradlew test --tests "*AuthServiceTest*"
```

### Run Tests by Category

```bash
# Run only unit tests (excludes integration tests)
./gradlew test --tests "com.ownfirebase.sdk.auth.*" \
               --tests "com.ownfirebase.sdk.data.*" \
               --tests "com.ownfirebase.sdk.analytics.*" \
               --tests "com.ownfirebase.sdk.realtime.*" \
               --tests "com.ownfirebase.sdk.OwnFirebase*"

# Run only integration tests (requires backend at localhost:8000)
./gradlew test --tests "com.ownfirebase.sdk.IntegrationTest"

# Run only auth tests (unit + advanced)
./gradlew test --tests "*Auth*Test"

# Run only Crashlytics and Storage tests
./gradlew test --tests "*Crashlytics*Test" --tests "*Storage*Test"
```

## Test Organization

### Unit Tests (No Backend Required)

```
AuthServiceTest (28 tests)
  ├─ Basic Auth (7)
  ├─ Social Auth (4)
  ├─ Phone/OTP (2)
  ├─ MFA (9)
  ├─ Magic Links (2)
  └─ Account Management (5)

DataServiceTest (16 tests)
  ├─ Collections (2)
  ├─ Documents (5)
  ├─ CRUD (5)
  └─ Advanced (3)

AnalyticsServiceTest (16 tests)
  ├─ Event Tracking (4)
  ├─ Event Listing (2)
  ├─ User Properties (2)
  ├─ Conversion Events (2)
  ├─ Queries (4)
  └─ Batch Operations (2)

RealtimeListenerTest (17 tests)
  ├─ Events (3)
  ├─ Document Listener (5)
  ├─ Collection Listener (5)
  └─ Advanced (4)

OwnFirebaseSDKTest (31 tests)
  ├─ Initialization (2)
  ├─ Service Access (7)
  ├─ Token Management (6)
  ├─ Lifecycle (6)
  ├─ Integration (4)
  ├─ Factory & Singleton (3)
  └─ Configuration Persistence (2)

AdvancedAuthFlowTest (12 tests)
  ├─ MFA Flows (3)
  ├─ Social Auth (1)
  ├─ Passwordless (2)
  ├─ Account Upgrade (1)
  ├─ Account Management (2)
  ├─ Authorization (1)
  ├─ Token Management (1)
  └─ Custom Tokens (1)

RemoteConfigServiceTest (13 tests)
  ├─ Parameters (5)
  ├─ Conditions (5)
  └─ Configuration (3)

CrashlyticsServiceTest (8 tests)
  ├─ Crash Reporting (4)
  ├─ Performance Tracing (2)
  ├─ Network Monitoring (1)
  └─ Summary (1)

StorageServiceTest (5 tests)
  ├─ Upload URLs (1)
  ├─ File Management (2)
  ├─ Metadata (1)
  └─ URLs (1)

OwnFirebaseTest (18 tests)
  └─ SDK Basics (18)
```

### Integration Tests (Requires Backend)

```
IntegrationTest (13 tests)
  ├─ Auth Integration (3)
  ├─ Data Integration (3)
  ├─ Analytics Integration (3)
  └─ Advanced Flows (4)
```

## Running Tests in CI/CD

### GitHub Actions Example

```yaml
name: Kotlin SDK Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up JDK 11
      uses: actions/setup-java@v3
      with:
        java-version: '11'
    
    - name: Run unit tests
      run: cd sdk/kotlin-sdk && ./gradlew test
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: sdk/kotlin-sdk/build/reports/tests/test/
```

### Local CI Simulation

```bash
#!/bin/bash
set -e

echo "=== Kotlin SDK Test Suite ==="
echo ""

cd sdk/kotlin-sdk

echo "[1/3] Running Unit Tests..."
./gradlew test --tests "*ServiceTest" --tests "*SDKTest" --tests "*FlowTest"

echo ""
echo "[2/3] Running Integration Tests (skip if no backend)..."
./gradlew test --tests "*IntegrationTest" || echo "Integration tests skipped"

echo ""
echo "[3/3] Generating Test Report..."
echo "Report available at: build/reports/tests/test/index.html"

echo ""
echo "=== Test Suite Complete ==="
```

## Test Output & Reporting

### Console Output

```bash
./gradlew test --info
```

Shows detailed information about:
- Test class compilation
- Test execution order
- Individual test results
- Timing information

### HTML Report

The Gradle test task automatically generates an HTML report:

**Location:** `sdk/kotlin-sdk/build/reports/tests/test/index.html`

**Contents:**
- Summary of all tests
- Breakdown by test class
- Individual test results
- Execution times
- Stack traces for failures

**View in browser:**
```bash
open sdk/kotlin-sdk/build/reports/tests/test/index.html
```

### JSON Test Results

Parse test results programmatically:

```bash
find build -name "*.xml" -path "*/test-results/*"
```

## Test Coverage

### Code Coverage Analysis

To add code coverage reporting, install and configure JaCoCo:

```bash
# Add to build.gradle.kts
plugins {
    kotlin("jvm") version "1.9.0"
    jacoco
}

jacoco {
    toolVersion = "0.8.8"
}

tasks.jacocoTestReport {
    dependsOn(tasks.test)
    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}
```

Then run:

```bash
./gradlew test jacocoTestReport
open build/reports/jacoco/test/html/index.html
```

## Troubleshooting

### Tests Not Found

**Issue:** `No tests found for given includes`

**Solution:**
```bash
# Check test file locations
find src/test/kotlin -name "*Test.kt"

# Verify test names end with "Test"
# Verify @Test annotations are present
```

### Gradle Wrapper Issues

**Issue:** `gradlew: command not found`

**Solution:**
```bash
# If gradlew doesn't exist, use gradle directly
gradle test

# Or create wrapper
gradle wrapper
```

### Out of Memory

**Issue:** `OutOfMemoryError` during tests

**Solution:**
```bash
# Increase heap size
export GRADLE_OPTS="-Xmx2048m"
./gradlew test

# Or in gradle.properties
org.gradle.jvmargs=-Xmx2048m
```

### Integration Tests Failing

**Issue:** Integration tests fail with connection errors

**Solution:**
```bash
# Start backend
python manage.py runserver 0.0.0.0:8000

# Then run integration tests
./gradlew test --tests "*IntegrationTest"

# Or skip integration tests
./gradlew test --tests "*" -x "*IntegrationTest*"
```

## Performance Tips

### Run Tests in Parallel

```bash
./gradlew test --parallel --max-workers=4
```

### Cache Test Results

```bash
./gradlew test --build-cache
```

### Run Only Changed Tests

```bash
./gradlew test --change-tracking
```

## Test Quality Metrics

### Lines of Test Code

```bash
find src/test/kotlin -name "*.kt" -exec wc -l {} + | tail -1
```

Expected output: ~5000+ lines of test code

### Test Count by Module

```bash
grep -r "@Test" src/test/kotlin --include="*.kt" | wc -l
```

Expected: 177+ tests

### Test Execution Time

```bash
./gradlew test --info 2>&1 | grep "Test execution took"
```

Expected: < 30 seconds for unit tests

## Continuous Monitoring

### Watch for Flaky Tests

Track tests that pass/fail inconsistently:

```bash
for i in {1..5}; do
  echo "Run $i:"
  ./gradlew test -q
  echo ""
done
```

### Generate Trend Reports

```bash
# Run tests weekly and collect results
0 0 * * 0 cd /path/to/sdk/kotlin-sdk && ./gradlew test > test-results-$(date +%Y-%m-%d).log
```

## Best Practices

1. **Run tests before committing:**
   ```bash
   ./gradlew test
   ```

2. **Run specific module tests when developing:**
   ```bash
   ./gradlew test --tests "*Auth*Test"
   ```

3. **Always check test report for failures:**
   ```bash
   open build/reports/tests/test/index.html
   ```

4. **Use meaningful assertions:**
   - Use `assertTrue()`, `assertEquals()`, `assertNotNull()`
   - Provide helpful assertion messages

5. **Keep tests isolated:**
   - No shared state between tests
   - Mock all external dependencies
   - Clean up in `@After` methods

## Integration Test Setup

### Prerequisites for Integration Tests

1. Backend running at `http://localhost:8000`
2. Database initialized
3. Valid project configuration

### Start Backend for Integration Tests

```bash
# In project root
python manage.py migrate
python manage.py runserver
```

### Run Integration Tests with Backend

```bash
# Terminal 1: Start backend
cd /path/to/backend
python manage.py runserver

# Terminal 2: Run tests
cd sdk/kotlin-sdk
./gradlew test --tests "*IntegrationTest"
```

## Test Documentation

### Test Description Format

Each test should be descriptive:

```kotlin
@Test
fun testLoginUser() {
    // Arrange: Set up test data
    val email = "user@example.com"
    val password = "password123"
    
    // Act: Perform the action
    val result = authService.login(email, password)
    
    // Assert: Verify the result
    assertNotNull(result.access)
    assertEquals("user@example.com", result.email)
}
```

### Documentation Comments

Add comments for complex test scenarios:

```kotlin
/**
 * Tests the complete TOTP MFA enrollment flow:
 * 1. Enroll TOTP secret
 * 2. Confirm TOTP with code
 * 3. Verify TOTP during login
 */
@Test
fun testTOTPEnrollmentFlow() {
    // ... test implementation
}
```

## Reporting Issues

When filing bugs related to tests:

1. Include test class and method name
2. Provide error output from `./gradlew test`
3. Note backend version and configuration
4. Include JDK version: `java -version`
5. Include OS: `uname -a`

## Next Steps

1. Run the full test suite: `./gradlew test`
2. Check test report: `open build/reports/tests/test/index.html`
3. Review coverage: Identify untested code
4. Add more tests for edge cases
5. Integrate with CI/CD pipeline
