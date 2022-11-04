*** Settings ***
Resource  cumulusci/robotframework/SalesforcePlaywright.robot
Library   Collections

Suite Setup     Open test browser
Suite Teardown  Close browser  ALL

Force Tags      playwright

*** Test Cases ***
Validate cci context in javascript keyword
    [Documentation]
    ...  Verify that keywords written in javascript have access
    ...  to some context information provided by the cumulusci
    ...  node module

    ${cci}=  Get library instance  cumulusci.robotframework.CumulusCI
    ${expected org info}=  Create dictionary
    ...  name          ${cci.org.name}
    ...  instance_url  ${cci.org.instance_url}
    ...  org_id        ${cci.org.org_id}

    ${expected project_config info}=  Create dictionary
    ...  repo_name     ${cci.project_config.repo_name}
    ...  repo_root     ${cci.project_config.repo_root}

    ${expected context}=  Create dictionary
    ...  org             ${expected org info}
    ...  project_config  ${expected project_config info}

    ${context}=  get cci context

    Dictionaries should be equal  ${context}  ${expected context}
