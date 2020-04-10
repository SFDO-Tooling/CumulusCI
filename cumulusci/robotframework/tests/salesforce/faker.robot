*** Settings ***
Resource  cumulusci/robotframework/Salesforce.robot
Force Tags  no-browser

*** Variables ***
${ssn}    ${faker.ssn()}

*** Test Cases ***
Faker variable should exist
    Variable should exist  \${faker}

Faker extended variable syntax in variables table
    Variable should exist  \${ssn}
    Should match regexp    ${ssn}  \\d\\d\\d-\\d\\d-\\d\\d\\d\\d

Faker keyword, no arguments
    # Note, ssn is used because it's easily to validate that
    # we got back data in the expected format. Hard to do with
    # names and addresses since the whole point is to provide
    # random fake data

    [Setup]  Variable should not exist   \${data}
    ${data}=  Get fake data  ssn
    Should match regexp    ${data}  \\d\\d\\d-\\d\\d-\\d\\d\\d\\d

Faker keyword, with arguments
    [Setup]  Variable should not exist   \${data}

    ${data}=  Get fake data  date  pattern=%Y,%m
    Should match regexp  ${data}  \\d\\d\\d\\d,\\d\\d

Faker variable, no arguments
    [Setup]  Variable should not exist   \${data}

    ${data}=  Set variable  ${faker.ssn()}
    Should match regexp    ${ssn}  \\d\\d\\d-\\d\\d-\\d\\d\\d\\d

Faker variable, with arguments
    [Setup]  Variable should not exist   \${data}

    ${data}=  Set variable  ${faker.date(pattern='%Y,%m')}
    Should match regexp  ${data}  \\d\\d\\d\\d,\\d\\d

Set faker locale
    [Setup]  Variable should not exist   \${data}
    [Teardown]  Set faker locale  en_US

    Set faker locale  fr_FR
    ${data}=  Get fake data  vat_id
    Should match regexp  ${data}  ^FR.*

    Set faker locale  it_IT
    ${data}=  Get fake data  vat_id
    Should match regexp  ${data}  ^IT.*

Set faker locale exception
    [Setup]  Variable should not exist   \${data}
    [Teardown]  Set faker locale  en_US

    Run keyword and expect error
    ...  Unknown locale for fake data: 'bogus'
    ...  Set faker locale  bogus

Faker keyword, bad property
    [Setup]  Variable should not exist   \${data}
    Run keyword and expect error
    ...  Unknown fake data request: 'bogus'
    ...  Get fake data  bogus
