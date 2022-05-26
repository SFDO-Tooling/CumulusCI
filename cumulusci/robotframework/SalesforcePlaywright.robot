*** Settings ***
Documentation
...  This resource file contains no keywords, but can be used to import
...  the most common libraries used for writing browser tests that use
...  the robotframework Browser library, based upon Playwright.
...
...  Note: when using this library, you cannot also use Salesforce.robot
...  or Salesforce.py since those are based on Selenium rather than Playwright.
...
...  Libraries imported by this resource file:
...  # *sigh* there's no good way to define these in just one place
...
...  - Browser
...  - Collections
...  - OperatingSystem
...  - String
...  - cumulusci.robotframework.CumulusCI
...  - cumulusci.robotframework.SalesforcePlaywright
...  - cumulusci.robotframework.SalesforceAPI
...
...  This resource file also defines the following variables, which can all be
...  overridden on the command line with the --vars option
...
...  | =Variable Name=          | = Default Value = |
...  | ${DEFAULT BROWSER SIZE}  | 1280x1024         |
...  | ${BROWSER}               | chrome            |

*** Variables ***
${DEFAULT BROWSER SIZE}  1280x1024
${BROWSER}               chrome

*** Settings ***
Library        Browser
Library        Collections
Library        OperatingSystem
Library        String
Library        cumulusci.robotframework.CumulusCI  ${ORG}
Library        cumulusci.robotframework.SalesforcePlaywright
Library        cumulusci.robotframework.SalesforceAPI
