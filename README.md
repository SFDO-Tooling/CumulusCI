# CumulusCI CLI

CumulusCI now provides a command line interface.  The CLI is evolving and not all functions are available through it yet.  You can find out more information about the CLI at https://github.com/SalesforceFoundation/CumulusCI/tree/master/cli

# CumulusCI

If you are already familiar with [Github Flow](http://scottchacon.com/2011/08/31/github-flow.html) and just want to get up and running using this process in the Salesforce platform, follow these steps:

1. Copy the files from the template directory into your own project
2. Fill in the properties
3. In your package.xml, add the "fullName" element as a child of "Package", like this:
    ```   
    <fullName>YourPackageName</fullName>
    ```
4. Clone CumulusCI in your CI server (Jenkins, Codeship,…)
5. Set a CUMULUSCI_PATH environment variable in the CI server that points to your forked copy
6. Set additional environment variables for your feature, master, beta, and packaging orgs, as seen below 
6. Set up your CI server. The main requirement is having Ant and the Salesforce Ant Migration Tool installed (just drop the jar in the ant lib directory). The server should run the ```deployCI``` ant target to deploy the unmanaged code and all the dependencies to an org
7. Make a commit to a branch to test everything works!

Environment variables:
```
SF_USERNAME_FEATURE
SF_PASSWORD_FEATURE
SF_SERVERURL_FEATURE

SF_USERNAME_MASTER
SF_PASSWORD_MASTER
SF_SERVERURL_MASTER

SF_USERNAME_BETA
SF_PASSWORD_BETA
SF_SERVERURL_BETA

SF_USERNAME_PACKAGING
SF_PASSWORD_PACKAGING
SF_SERVERURL_PACKAGING
```
