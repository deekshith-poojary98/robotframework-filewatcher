# Release Notes

## robotframework-filewatcher v0.2.0

**Release Date:** June 24, 2026

### 🚀 Overview

`robotframework-filewatcher` v0.2.0 introduces expanded filesystem validation and event history utilities for Robot Framework.

This release adds checksum-based file assertions, directory-empty waits, file size conditions, and event-derived file history helpers while preserving the library's existing event-driven behavior.

---

## ✨ Highlights

### New Validation and History Keywords

* `File Should Be Stable`
* `Wait Until File Does Not Exist`
* `Get Oldest File`
* `Get File Checksum`
* `File Checksum Should Be`
* `Wait For Any File Event`
* `Wait For File Moved`
* `Get Event Statistics`
* `Wait Until Directory Is Empty`
* `Wait Until File Size Is`
* `Wait Until File Checksum Changes`
* `Get New Files Since`
* `Get Deleted Files Since`
* `File Should Not Change`

### Usability Improvements

* Extended waiting keywords for file stability and content change detection.
* Added checksum streaming for large files.
* Improved event history retrieval for created, moved, and deleted files.

### Testing and Documentation

* Added new unit tests and Robot Framework acceptance coverage for all new keywords.
* Updated README documentation and examples.

---

## robotframework-filewatcher v0.1.0

**Release Date:** June 23, 2026

### 🚀 Overview

`robotframework-filewatcher` v0.1.0 marks the first public release of an event-driven filesystem monitoring library for Robot Framework.

Built on top of Python's `watchdog`, the library provides a thread-safe event store, filesystem event history, and high-level Robot Framework keywords for waiting, querying, and validating filesystem activity without relying on polling or arbitrary sleeps.

This release establishes a stable foundation for future enhancements while already supporting many common automation scenarios such as generated report validation, export workflows, batch file processing, and filesystem event monitoring.

---

## ✨ Highlights

### Event-Driven File Monitoring

Monitor filesystem changes using native operating system events instead of repeatedly polling directories.

Supported events:

* Created
* Modified
* Deleted
* Moved

### Thread-Safe Event Store

* Historical event retention
* Non-consuming event reads
* Multiple concurrent waiters
* Sequential event IDs
* Bounded memory usage

### High-Level Robot Framework Keywords

#### Watching

* Start Watching Directory
* Stop Watching Directory
* Is Watching Directory
* Get Watched Directories

#### Waiting

* Wait For File Created
* Wait For File Modified
* Wait For File Deleted
* Wait Until File Stable
* Wait Until Directory Is Not Empty
* Wait Until File Count Is

#### Discovery

* Get Latest File
* Find Files Matching Pattern
* Get File Count

#### Events

* Get File Events
* Get File Events Since
* Get Current Event Id
* Get Event Types
* Clear Event History
* Should Have File Event

---

## 📝 Improvements in v0.1.0

* Standardized keyword docstrings for improved readability.
* Enhanced Robot Framework Libdoc documentation generation.
* Added `Get Event Types` helper keyword.
* Updated unit tests and Robot Framework acceptance tests.
* Improved GitHub Actions CI pipeline.
* Added automated documentation generation workflow.
* Added documentation badge and project improvements to README.

---

## 🔧 CI & Documentation

The project now includes:

* Automated unit tests
* Robot Framework acceptance tests
* Automated Libdoc generation
* GitHub Actions workflows for CI and documentation
* Generated keyword documentation hosted via GitHub Pages

---

## 📦 Installation

From PyPI:

```bash
pip install robotframework-filewatcher
```

From source:

```bash
git clone https://github.com/deekshith-poojary98/robotframework-filewatcher.git

cd robotframework-filewatcher

pip install -e .
```

---

## 🧪 Validation

This release has been validated through:

* Python unit tests (`pytest`)
* Robot Framework acceptance tests
* Wheel and source distribution builds
* Fresh virtual environment installation tests
* Robot Framework Libdoc generation

---

## 📌 Known Limitations

* Browser-specific download handling is not included in this release.
* OS-level watch limits (such as Linux `inotify` limits) depend on system configuration.
* Advanced download lifecycle keywords are planned for future releases.

---

## 🎯 What's Next

Potential future enhancements:

* Native `Wait For Download` support
* Download temporary file handling (`.crdownload`, `.part`)
* Checksum verification keywords
* File archiving and compression helpers
* Advanced event filtering APIs

---

Thank you for trying **robotframework-filewatcher**.

**Stop polling files. Start waiting for events.**
