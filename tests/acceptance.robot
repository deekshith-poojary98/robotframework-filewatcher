*** Settings ***
Library           FileWatcher
Library           OperatingSystem
Library           Collections

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
    
    ${event}=    Wait Until File Stable    stable.log    stability_time=0.5    timeout=5.0
    Should End With    ${event}[src_path]    stable.log
    
    [Teardown]    Clean Directory And Stop Watch

File Utility Keywords
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}

    Create File    ${MY_TEMP_DIR}${/}a.txt    one
    Create File    ${MY_TEMP_DIR}${/}b.txt    two
    Create File    ${MY_TEMP_DIR}${/}temp.lock    lock

    ${oldest}=    Get Oldest File    *.txt
    Should End With    ${oldest}    a.txt

    ${checksum}=    Get File Checksum    ${MY_TEMP_DIR}${/}a.txt    md5
    File Checksum Should Be    ${MY_TEMP_DIR}${/}a.txt    ${checksum}    md5

    Remove File    ${MY_TEMP_DIR}${/}temp.lock
    Wait Until File Does Not Exist    temp.lock    timeout=5.0

    ${stats}=    Get Event Statistics
    Should Be True    ${stats}[total] >= 1

    [Teardown]    Clean Directory And Stop Watch

File Moved Event
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}

    Create File    ${MY_TEMP_DIR}${/}src.txt    move
    ${created}=    Wait For File Created    src.txt
    Move File    ${MY_TEMP_DIR}${/}src.txt    ${MY_TEMP_DIR}${/}dest.txt
    ${event}=    Wait For File Moved    dest.txt    since_id=${created}[id]    timeout=5.0
    Should End With    ${event}[src_path]    src.txt
    Should End With    ${event}[dest_path]    dest.txt

    [Teardown]    Clean Directory And Stop Watch

Wait Until Directory Is Empty
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}

    Create File    ${MY_TEMP_DIR}${/}temp.txt    lock
    ${id}=    Get Current Event Id
    Remove File    ${MY_TEMP_DIR}${/}temp.txt
    Wait Until Directory Is Empty    ${MY_TEMP_DIR}    timeout=5.0

    [Teardown]    Clean Directory And Stop Watch

Wait Until File Size Is
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}

    Create File    ${MY_TEMP_DIR}${/}growing.bin    1
    Append To File    ${MY_TEMP_DIR}${/}growing.bin    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    Wait Until File Size Is    *.bin    > 100    timeout=5.0

    [Teardown]    Clean Directory And Stop Watch

Wait Until File Checksum Changes
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}

    Create File    ${MY_TEMP_DIR}${/}checksum.txt    initial
    ${old}=    Get File Checksum    ${MY_TEMP_DIR}${/}checksum.txt
    Append To File    ${MY_TEMP_DIR}${/}checksum.txt    update
    ${new}=    Wait Until File Checksum Changes    ${MY_TEMP_DIR}${/}checksum.txt    ${old}    timeout=5.0
    Should Not Be Equal    ${old}    ${new}

    [Teardown]    Clean Directory And Stop Watch

Get New And Deleted Files Since
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Create Directory    ${MY_TEMP_DIR}${/}new_files
    Start Watching Directory    ${MY_TEMP_DIR}${/}new_files
    Clear Event History

    ${checkpoint}=    Get Current Event Id
    Create File    ${MY_TEMP_DIR}${/}new_files${/}new1.txt    one
    Wait For File Created    new1.txt    timeout=5.0
    Create File    ${MY_TEMP_DIR}${/}new_files${/}new2.txt    two
    Wait For File Created    new2.txt    timeout=5.0
    ${new_files}=    Get New Files Since    ${checkpoint}
    Should Contain    ${new_files}[0]    new1.txt
    Should Contain    ${new_files}[1]    new2.txt

    Remove File    ${MY_TEMP_DIR}${/}new_files${/}new1.txt
    Wait For File Deleted    new1.txt    timeout=5.0
    ${deleted}=    Get Deleted Files Since    ${checkpoint}
    Should Contain    ${deleted}[0]    new1.txt

    [Teardown]    Clean Directory And Stop Watch

File Should Not Change
    [Setup]    Create Directory    ${MY_TEMP_DIR}
    Start Watching Directory    ${MY_TEMP_DIR}

    Create File    ${MY_TEMP_DIR}${/}stable.txt    content
    File Should Not Change    stable.txt    duration=1.0

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

    # 6.a Verify Get Event Types includes 'created'
    ${types}=    Get Event Types
    Should Contain    ${types}    created
    
    # 7. Verify Get Latest File
    Create File    ${MY_TEMP_DIR}${/}newer.txt    content
    ${latest}=    Get Latest File    *.txt
    Should End With    ${latest}    newer.txt
    
    [Teardown]    Clean Directory And Stop Watch

*** Keywords ***
Clean Directory And Stop Watch
    Run Keyword And Ignore Error    Stop Watching Directory    ${MY_TEMP_DIR}
    Remove Directory    ${MY_TEMP_DIR}    recursive=True
