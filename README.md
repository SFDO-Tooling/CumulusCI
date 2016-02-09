# CumulusCI CLI

CumulusCI now provides a command line interface.  The CLI is evolving and not all functions are available through it yet.  You can try it out with the following steps:

    cd $CUMULUSCI_PATH
    git fetch --all
    git checkout features/cloud-ci-integrations
    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

    # To activate the CLI, you need to activate the virtualenv where you installed it
    source $CUMULUSCI_PATH/venv/bin/activate

# CumulusCI

If you are already familiar with [Github Flow](http://scottchacon.com/2011/08/31/github-flow.html) and just want to get up and running using this process in the Salesforce platform, follow these steps:

1. Copy the files from the template directory into your own project
2. Fill in the properties
3. In your package.xml, add the "fullName" element as a child of "Package", like this:

    ```   
    <fullName>YourPackageName</fullName>
    ```

4. Set up your CI server (Jenkins, Codeship,…)
5. Clone CumulusCI in your CI server
6. Set a CUMULUSCI_PATH environment variable in the CI server that points to your forked copy
7. Make a commit to a branch to test everything works!
