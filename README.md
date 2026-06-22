![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Robot Framework 7+](https://img.shields.io/badge/robot%20framework-7%2B-lightgrey)
![License Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)

# robotframework-filewatcher

A modern Robot Framework library for event-driven filesystem testing.

`robotframework-filewatcher` allows Robot Framework tests to monitor file creation, modification, deletion, and file stability using native OS filesystem events powered by `watchdog`.

Unlike polling-based approaches, FileWatcher maintains a thread-safe event history, supports multiple concurrent waiters, and provides high-level Robot Framework keywords for waiting, querying, and validating filesystem activity.

Supports:

- Windows
- Linux
- macOS

Perfect for:

- Download verification
- Generated report validation
- Export/import workflow testing
- Batch file processing
- Background file synchronization
- Event-driven automation pipelines

---

## Why FileWatcher?

Traditional Robot Framework file checks often become:

```robot
FOR    ${i}    IN RANGE    30
    File Should Exist    report.xlsx
    Sleep    1s
END
```

That is slow, brittle, and prone to race conditions.

With FileWatcher:

```robot
Start Watching Directory    ${DOWNLOADS}
Click Export
${event}=    Wait For File Created    report.xlsx
Log    ${event}[src_path]
```

No polling. No arbitrary sleeps. No flaky timing.

---

## Architecture

FileWatcher is built around:

- A single shared `watchdog.Observer`
- `DirectoryEventHandler` converting OS events into file events
- A thread-safe `EventStore`
- Non-consuming historical event retention
- Multiple concurrent waiters and keyword consumers
- Bounded memory storage for safety

```
OS Events
  ↓
watchdog Observer
  ↓
DirectoryEventHandler
  ↓
EventStore
  ↓
Robot Framework Keywords
```

---

## Feature Matrix

| Category | Keywords |
| --- | --- |
| Watching | `Start Watching Directory`, `Stop Watching Directory`, `Is Watching Directory`, `Get Watched Directories` |
| Waiting | `Wait For File Created`, `Wait For File Modified`, `Wait For File Deleted`, `Wait Until File Stable`, `Wait Until Directory Is Not Empty`, `Wait Until File Count Is` |
| Discovery | `Get Latest File`, `Find Files Matching Pattern`, `Get File Count` |
| Events | `Get File Events`, `Get File Events Since`, `Get Current Event Id`, `Clear Event History`, `Should Have File Event` |

---

## Quick Start

Install from the repository:

```bash
pip install .
```

Install development dependencies:

```bash
pip install -e ".[dev]"
```

---

## Simple Example

```robot
*** Settings ***
Library    FileWatcher

*** Test Cases ***
Wait For Generated Report
    Start Watching Directory    ${DOWNLOAD_DIR}
    Click Button    Generate Report
    ${event}=    Wait For File Created    report.xlsx
    Log    Generated report path: ${event}[src_path]
```

---

## Common Use Cases

- Wait for browser downloads to complete
- Validate generated report files
- Monitor export and import workflows
- Track batch file production
- Detect deleted files or cleanup actions
- Observe background processes writing to disk

---

## Example Robot Framework Usage

```robot
*** Settings ***
Library    FileWatcher
Library    OperatingSystem

Suite Teardown    Clean Up Watches

*** Variables ***
${DOWNLOAD_DIR}    ${CURDIR}${/}downloads

*** Test Cases ***
Verify File Stability
    [Setup]    Run Keywords    Create Directory    ${DOWNLOAD_DIR}    AND    Clear Event History
    Start Watching Directory    ${DOWNLOAD_DIR}

    Create File    ${DOWNLOAD_DIR}${/}report_draft.xlsx    Initial chunk...
    ${event}=    Wait Until File Stable    report_draft.xlsx    stability_time=1.0    timeout=10.0
    Log To Console    File stabilized at path: ${event}[src_path]

    ${since_id}=    Set Variable    ${event}[id]
    Append To File    ${DOWNLOAD_DIR}${/}report_draft.xlsx    Final chunk.
    ${mod_event}=    Wait For File Modified    report_draft.xlsx    since_id=${since_id}
    Log To Console    Updated event recorded: ${mod_event}

*** Keywords ***
Clean Up Watches
    Stop Watching Directory    ${DOWNLOAD_DIR}
    Remove Directory    ${DOWNLOAD_DIR}    recursive=True
```

---

## Running Tests

```bash
pytest
```

```bash
PYTHONPATH=src robot tests/acceptance.robot
```

---

## License

Apache-2.0
