## ✅ Current Status

* Basic tests (404/444) are passing.

## 🔴 Priority Problem: Architecture Violations

The main issue is **4 critical violations** of Domain-Driven Design (DDD) principles, causing tight coupling:

1.  **Domain depends on external libraries:** The domain layer incorrectly imports and uses `yt-dlp` and Python's `logging` module.
2.  **Domain knows infrastructure exceptions:** The domain layer categorizes `yt-dlp` specific errors.
3.  **Application depends on Infrastructure:** Services in the application layer directly import concrete infrastructure classes (like `StorageService`) instead of domain interfaces.
4.  **Tasks depend on Infrastructure:** A background task directly accesses a GCS repository instead of calling an application service.

- The goal is to decouple the layers, following DDD rules.
- Move infrastructure-specific error categorization (like `categorize_ytdlp_error`) out of the Domain and into the Application layer.
- Remove all `logging` calls from the Domain layer. Use domain events to signal errors, and let the infrastructure layer handle the actual logging.
- Move all `yt-dlp` logic from the Domain to the Infrastructure layer. The Domain will only define an interface (e.g., `IVideoMetadataExtractor`), which the application will use.
- All changes must maintain >=90% test coverage.
* **Dual DI Patterns:** Simplify by removing the `ServiceLocator` and only using the `DependencyContainer`.
* **Dual File Storage:** Consolidate two separate local file storage classes into one more generic (accepts local, GCS, S3, etc).
* ~~**Performance Monitoring:** Remove ~300 lines of performance logging infrastructure if it's not being actively monitored.~~ ✅ **COMPLETED** - No custom performance monitoring infrastructure exists. Documentation updated to reflect use of standard logging and external tools.
* **`DownloadResult` Object:** Replace the complex 79-line value object with a simple tuple or dataclass for success/failure.
* **EventPublisher:** An event system is over-engineered for only one subscriber.
