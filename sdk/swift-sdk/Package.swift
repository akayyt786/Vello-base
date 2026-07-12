// swift-tools-version:5.9
import PackageDescription

let package = Package(
  name: "OwnFirebaseSDK",
  platforms: [
    .iOS(.v14),
    .macOS(.v11),
    .tvOS(.v14),
    .watchOS(.v7)
  ],
  products: [
    .library(
      name: "OwnFirebaseSDK",
      targets: ["OwnFirebaseSDK"]
    ),
  ],
  dependencies: [
    // No external dependencies - using only Foundation
  ],
  targets: [
    .target(
      name: "OwnFirebaseSDK",
      dependencies: [],
      path: "Sources/OwnFirebaseSDK"
    ),
    .testTarget(
      name: "OwnFirebaseSDKTests",
      dependencies: ["OwnFirebaseSDK"],
      path: "Tests"
    ),
  ]
)
