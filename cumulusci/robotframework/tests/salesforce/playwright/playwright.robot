*** Settings ***
Resource         cumulusci/robotframework/SalesforcePlaywright.robot

Suite Setup      Open test browser
Suite Teardown   Close browser  ALL
Force Tags       playwright

*** Test Cases ***

Go to user profile
    Click    button:has-text("View profile")
    Click    .profile-card-name .profile-link-label

    Wait until network is idle
    Take screenshot

Go to contacts home
    Click            button:has-text("App Launcher")
    Fill text        input[placeholder='Search apps and items...']  Contacts
    Click            one-app-launcher-menu-item:has-text("Contacts")

    Wait until network is idle
    Take screenshot
