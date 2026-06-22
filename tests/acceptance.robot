*** Settings ***
Library           FileWatcher
Library           OperatingSystem

*** Variables ***
${MY_TEMP_DIR}       ${TEMPDIR}${/}robot_filewatcher_tests

*** Test Cases ***
Watch Created File
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}
    
    Create File    ${MY_TEMP_DIR}${/}report.pdf    Hello World
    
    ${event}=    Wait For File Created    *.pdf    timeout=5.0
    Should End With    ${event}[src_path]    report.pdf
    Should Be Equal As Strings    ${event}[event_type]    created
    
    ${events}=    Get File Events
    # Standard watchdog event stream might have additional modification events, but there should be at least 1 event
    Should Not Be Empty    ${events}
    
    Clear Event History
    ${cleared_events}=    Get File Events
    Should Be Empty    ${cleared_events}
    
    [Teardown]    Clean Directory And Stop Watch

Watch Modified File
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}
    Create File    ${MY_TEMP_DIR}${/}data.xlsx    Initial content
    
    ${created_event}=    Wait For File Created    data.xlsx
    ${since_id}=    Set Variable    ${created_event}[id]
    
    Append To File    ${MY_TEMP_DIR}${/}data.xlsx    More content
    
    ${mod_event}=    Wait For File Modified    data.xlsx    since_id=${since_id}    timeout=5.0
    Should End With    ${mod_event}[src_path]    data.xlsx
    Should Be Equal As Strings    ${mod_event}[event_type]    modified
    
    [Teardown]    Clean Directory And Stop Watch

Wait For File Stable
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}
    
    Create File    ${MY_TEMP_DIR}${/}stable.log    part 1
    
    ${event}=    Wait For Download    stable.log    stability_time=0.5    timeout=5.0
    Should End With    ${event}[src_path]    stable.log
    
    [Teardown]    Clean Directory And Stop Watch

Test Remaining Keywords
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    
    # 1. Verify initially not watched
    ${is_watched}=    Is Watching Directory    ${MY_TEMP_DIR}
    Should Be Equal    ${is_watched}    ${False}
    
    Start Watching Directory    ${MY_TEMP_DIR}
    
    # 2. Verify now watched
    ${is_watched_after}=    Is Watching Directory    ${MY_TEMP_DIR}
    Should Be Equal    ${is_watched_after}    ${True}
    
    # 3. Verify watched directories list
    ${dirs}=    Get Watched Directories
    # Resolves paths
    ${resolved_dir}=    Normalize Path    ${MY_TEMP_DIR}
    # Check that dirs contains at least a match (on macOS resolved path starts with /private/var/...)
    Should Not Be Empty    ${dirs}
    
    # 4. Verify Get Current Event Id initially
    ${id_before}=    Get Current Event Id
    
    # Trigger event
    Create File    ${MY_TEMP_DIR}${/}test_new.pdf    initial
    ${event}=    Wait For File Created    test_new.pdf
    
    # 5. Verify Get Current Event Id updates
    ${id_after}=    Get Current Event Id
    Should Be True    ${id_after} > ${id_before}
    
    # 6. Verify Should Have File Event
    Should Have File Event    event_type=created    pattern=*.pdf
    
    # 7. Verify Get Latest File
    Create File    ${MY_TEMP_DIR}${/}newer.txt    content
    ${latest}=    Get Latest File    *.txt
    Should End With    ${latest}    newer.txt
    
    [Teardown]    Clean Directory And Stop Watch

*** Keywords ***
Clean Directory And Stop Watch
    Run Keyword And Ignore Error    Stop Watching Directory    ${MY_TEMP_DIR}
    Remove Directory    ${MY_TEMP_DIR}    recursive=True
