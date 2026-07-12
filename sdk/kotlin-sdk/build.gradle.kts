plugins {
    kotlin("jvm") version "1.9.0"
    id("maven-publish")
}

group = "com.ownfirebase"
version = "1.0.0"

repositories {
    mavenCentral()
}

dependencies {
    // HTTP client
    implementation("com.squareup.okhttp3:okhttp:4.11.0")

    // JSON serialization
    implementation("com.google.code.gson:gson:2.10.1")

    // Kotlin stdlib
    implementation(kotlin("stdlib"))

    // Coroutines for async/await
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.1")

    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.1")
    testImplementation("org.mockito.kotlin:mockito-kotlin:5.1.0")
    testImplementation("org.mockito:mockito-core:5.2.1")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.11.0")
    testImplementation("com.google.truth:truth:1.1.3")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.0")
}

tasks.test {
    useJUnit()

    // Test reporting
    testLogging {
        events("passed", "skipped", "failed")
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
        showStandardStreams = false
    }

    // Show summary
    addTestListener(object : org.gradle.api.tasks.testing.TestListener {
        override fun beforeTest(test: org.gradle.api.tasks.testing.TestDescriptor) {}
        override fun afterTest(test: org.gradle.api.tasks.testing.TestDescriptor, result: org.gradle.api.tasks.testing.TestResult) {}
        override fun beforeSuite(suite: org.gradle.api.tasks.testing.TestDescriptor) {}
        override fun afterSuite(suite: org.gradle.api.tasks.testing.TestDescriptor, result: org.gradle.api.tasks.testing.TestResult) {
            if (suite.parent == null) {
                println("\n" + "=".repeat(70))
                println("Test Results: ${result.testCount} tests")
                println("  Passed:  ${result.successfulTestCount}")
                println("  Failed:  ${result.failedTestCount}")
                println("  Skipped: ${result.skippedTestCount}")
                println("=".repeat(70) + "\n")
            }
        }
    })
}

kotlin {
    jvmToolchain(17)
}

publishing {
    publications {
        create<MavenPublication>("maven") {
            from(components["kotlin"])
        }
    }
}
