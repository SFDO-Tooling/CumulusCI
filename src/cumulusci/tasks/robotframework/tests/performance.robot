*** Settings ***

Resource        cumulusci/robotframework/Salesforce.robot
Resource        cumulusci/robotframework/CumulusCI.robot
Test Teardown   Delete Session Records
Force Tags      api  no-browser

*** Test Cases ***
Test FOR and IF statements
    # the parser changed in robot 4.x, and part of that change
    # caused the performance code to crap out on FOR and IF
    # statements (FOR now appears in the internal model
    # as a keyword element rather than a "for" element, and IF
    # is also rendered as a keyword. *sigh*)
    [tags]  perf
    FOR  ${i}  IN  xyzzy  plugh
        IF  $i == 'xyzzy'
            Set test metric  xyzzy  2
        ELSE IF  $i == 'plugh'
            Set test metric  plugh  4
        END
    END
#    set test metric  plugh  2
